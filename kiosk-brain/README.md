# Kiosk Brain — Raspberry Pi 5 (4GB) Application

The kiosk-brain is the intelligent application layer of the Smart ID Card Distribution Kiosk, running on Raspberry Pi 5 (4GB) with Python 3.11. It manages the entire student-facing and staff-facing workflow, OCR image processing, authentication, database persistence, SMS dispatch, and hardware control via SPI protocol.

## Architecture Overview

### High-Level Control Flow

```bash
IDLE Screen
    ↓ [on touch/swipe events]
    ├─→ Staff Door Unlock Path
    │    └─ STAFF_PIN Screen (bcrypt PIN validation)
    │         ├─→ [3× fail] LOCKED Screen (24h hard lockout)
    │         └─→ [correct] CHECKLIST Screen
    │              ├─ Pre-scan validation (staff device serial, time, batch count)
    │              └─ BATCH Progress Screen
    │                  ├─ Conveyor 1 IR trigger → CSI camera capture
    │                  ├─ OCR pipeline (OpenCV preprocessing + Tesseract extraction)
    │                  ├─ [OCR fail] → Servo flap divert to reject bin
    │                  ├─ [OCR pass] → Regex validation + confidence gating
    │                  ├─ HTTPS query university API → student data fetch
    │                  ├─ [API timeout] → queue card as pending_lookup, retry background
    │                  ├─ SPI ROTATE_TO_SLOT (assign carousel position)
    │                  ├─ Africa's Talking SMS dispatch (OTP for returning, OTP+PIN for first-year)
    │                  └─ Loop until conveyor empty → SUMMARY (batch complete)
    │
    └─→ Student Card Collection Path
         ├─→ HOME Screen (path selector)
         │    ├─→ Button [Collection with OTP]
         │    │    └─ OTP Screen (6-digit input, rate-limited resend)
         │    │         ├─ [3× fail] 30-min soft lockout
         │    │         └─ [correct] PIN_SELECT Screen
         │    │              └─ [existing PIN path or temp PIN + force-change]
         │    │
         │    └─→ Button [Expired Card Scan]
         │         ├─ Servo latch activates (card clamped in slot)
         │         ├─ USB camera frame capture (expired card registration number)
         │         ├─ OCR extracts reg number
         │         ├─ Lookup student in SQLite
         │         └─ → OTP Screen (same as above)
         │
         ├─→ PIN Screen (4–6 digit, bcrypt verified)
         │    ├─ [3× fail] 24h hard lockout (audited for administrator)
         │    └─ [correct] CONFIRM Screen
         │
         ├─→ CONFIRM Screen (show student name, programme, card info)
         │    ├─ [confirm button] → SUCCESS
         │    │    ├─ SPI ROTATE_TO_SLOT(assigned_index)
         │    │    ├─ SPI EJECT_CARD (servo push from front gate)
         │    │    ├─ [eject success] → StudentCollection audit event
         │    │    └─ Timer 30s → auto-logout back to IDLE
         │    │
         │    └─ [cancel button] → IDLE (cascade: Servo RELEASE_CARD, SMS notification)
         │
         └─→ LOCKED Screen (24h hard lockout)
              └─ [display admin contact info]
              └─ Auto-logout after 60s
```

### Module Responsibilities

| Module               | Purpose                                                        | Key Dependencies           |
| -------------------- | -------------------------------------------------------------- | -------------------------- |
| `main.py`            | Kivy app entry point, ScreenManager initialization             | Kivy, config, logging      |
| `config.py`          | Environment variables, API keys, timeout constants             | pathlib, os                |
| `api_client.py`      | HTTPS wrapper for university DB (with mDNS support)            | requests, urllib3          |
| `auth.py`            | OTP generation, bcrypt PIN verification, lockout state machine | bcrypt, secrets, sqlite3   |
| `database.py`        | SQLite schema, transactions, batch operations                  | sqlite3, datetime          |
| `ocr.py`             | Image preprocessing, Tesseract invocation, regex validation    | opencv-python, pytesseract |
| `session_manager.py` | Per-session state lifecycle, explicit teardown                 | dataclasses                |
| `sms_client.py`      | Africa's Talking SDK wrapper, retry queue                      | africastalking             |
| `spi_master.py`      | SPI frame encoding, checksum, command dispatch                 | spidev                     |
| `ui/screens.py`      | Kivy Screen subclasses, event handlers                         | Kivy                       |
| `ui/styles.kv`       | Widget layouts, event bindings                                 | Kivy (.kv DSL)             |

## Installation & Configuration

### Prerequisites

- **Python 3.11**: Required for type hints and performance

  ```bash
  sudo apt install python3.11 python3.11-venv
  ```

- **System Libraries**

  ```bash
  # For OpenCV and Tesseract
  sudo apt install libopencv-dev libsm6 libxrender-dev libxext-dev
  sudo apt install tesseract-ocr libtesseract-dev
  sudo apt install libatlas-base-dev libjasper-dev libtiff5 libharfbuzz0b libwebp6

  # For SPI communication
  sudo apt install python3-spidev

  # For mDNS support
  sudo apt install avahi-daemon
  ```

### Python Virtual Environment

```bash
cd kiosk-brain
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
```

### Configuration File (`config.py`)

```python
# config.py structure — CRITICAL for deployment

API_KEY_UNIVERSITY = "your-api-key-here"  # Bearer auth
API_KEY_AFRICAS_TALKING = "your-at-api-key"
SMS_SENDER_NAME = "UNIV_ID"

UNIVERSITY_BASE_URL = "http://university-db.local:5000"  # mDNS resolution
UNIVERSITY_API_TIMEOUT = 5.0  # seconds
UNIVERSITY_API_RETRIES = 3

SMS_GATEWAY_TIMEOUT = 10.0
SMS_RETRY_INTERVAL = 900  # 15 minutes

OTP_LENGTH = 6
OTP_VALIDITY_HOURS = 24
OTP_RETRY_SOFT_LOCKOUT_MINUTES = 30
OTP_MAX_ATTEMPTS = 3

PIN_LENGTH_MIN = 4
PIN_LENGTH_MAX = 6
PIN_MAX_ATTEMPTS = 3
PIN_LOCKOUT_HOURS = 24

STAFF_PIN = "b'$2b$12$...'"  # bcrypt hash (pre-computed, never store plaintext)
STAFF_PIN_MAX_ATTEMPTS = 3
STAFF_PIN_LOCKOUT_HOURS = 24

KIVY_WINDOW_WIDTH = 800
KIVY_WINDOW_HEIGHT = 480
KIVY_FONT_SIZE_TITLE = 24
KIVY_FONT_SIZE_NORMAL = 18

SESSION_IDLE_TIMEOUT_SECONDS = 90  # Auto-logout duration
SESSION_COLLECTION_SUCCESS_DISPLAY_SECONDS = 30

OCR_CONFIDENCE_THRESHOLD = 0.95
OCR_TESSERACT_CONFIG = "--psm 7 --dpi 300"
OCR_TIMEOUT_SECONDS = 5.0

DATABASE_PATH = "/home/pi/card-issuance-system/kiosk-brain/data/kiosk.db"
LOG_PATH = "/home/pi/card-issuance-system/kiosk-brain/data/logs"

SPI_DEVICE = "/dev/spidev0.0"
SPI_SPEED_HZ = 1_000_000  # 1 MHz clock

# Email for escalated audit events (admin review)
ADMIN_CONTACT_EMAIL = "admin@university.edu"
ADMIN_CONTACT_PHONE = "+255..."
```

⚠️ **Security Note**: Never commit `config.py` with real API keys. Use environment variables:

```bash
export AFRICAS_TALKING_KEY="..."
export UNIVERSITY_API_KEY="..."
```

### Database Initialization

```bash
cd db
python init_db.py
```

This creates `kiosk.db` with tables: `students`, `authentication`, `audit_log`, `batches`, `sessions`.

## Python Modules Reference

### `api_client.py`

**Purpose**: HTTPS wrapper for university student database with automatic mDNS resolution.

**Public Interface**:

```python
class UniversityAPIClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 5.0):
        pass

    def get_student(self, reg_number: str) -> dict:
        """
        Fetch student data by registration number.

        Returns:
            {
                "reg_number": "T/UDSM/0001/2021",
                "name": "Jane Doe",
                "programme": "Computer Science",
                "phone": "+255123456789",
                "status": "active" | "inactive" | "suspended"
            }

        Raises:
            APITimeoutError: If request exceeds timeout
            APIConnectionError: If network unavailable
            StudentNotFoundError: If reg_number not exists
        """
```

**Error Handling**:

- Timeouts: 5-second hard limit, 3 retries with exponential backoff (1s, 2s, 4s)
- Network failure: Card queued in `batches` table as `pending_lookup`, background thread retries every 2 minutes
- HTTP 404: Student record not found, card stored with status `missing_student`
- HTTP 403 (inactive/suspended): Card stored with status `hold`, no SMS dispatched

### `auth.py`

**Purpose**: Two-factor authentication with bcrypt hashing and lockout state machine.

**Public Interface**:

```python
class AuthenticationManager:
    def __init__(self, db_path: str):
        pass

    def generate_otp(self) -> str:
        """
        Generate 6-digit OTP using secrets.randbelow(1_000_000).
        Returns zero-padded string "000123".
        """

    def store_otp(self, reg_number: str, otp: str, validity_hours: int = 24) -> bool:
        """
        Hash OTP with bcrypt, store in DB with expiry timestamp.
        Returns True if successful.
        """

    def verify_otp(self, reg_number: str, otp_input: str) -> tuple[bool, str]:
        """
        Verify OTP against stored hash.

        Returns:
            (True, "valid") - OTP correct and within 24h window
            (False, "expired") - Correct but > 24h old
            (False, "mismatch") - Wrong OTP
            (False, "soft_lockout_30min") - 3× consecutive failures
        """

    def generate_pin(self) -> str:
        """Generate temporary PIN for first-year students."""

    def verify_pin(self, reg_number: str, pin_input: str) -> tuple[bool, str]:
        """
        Verify PIN against bcrypt hash.

        Returns:
            (True, "valid") - PIN correct
            (False, "mismatch") - Wrong PIN
            (False, "hard_lockout_24h") - 3× consecutive failures (audited)

        Also tracks lockout event in audit_log for administrator review.
        """

    def set_pin(self, reg_number: str, new_pin: str) -> bool:
        """
        Store new PIN as bcrypt hash. Called on first-year student's
        first collection visit (forces temporary PIN change).
        """
```

**Lockout Events Logged to `audit_log`**:

- `otp_verify_fail`: Each incorrect OTP attempt
- `otp_lockout`: Soft lockout after 3 OTP failures (30 minutes)
- `pin_verify_fail`: Each incorrect PIN attempt
- `pin_lockout`: Hard lockout after 3 PIN failures (24 hours, escalated to admin)

### `database.py`

**Purpose**: SQLite wrapper with transaction management and batch operations.

**Public Interface**:

```python
class KioskDatabase:
    def __init__(self, db_path: str):
        pass

    def add_student(self, reg_number: str, name: str, programme: str,
                    phone: str, status: str = "active") -> bool:
        """Insert student record (called after university API fetch)."""

    def get_student(self, reg_number: str) -> dict | None:
        """Lookup student by registration number."""

    def add_card_batch(self, batch_id: str, staff_id: str, count: int) -> bool:
        """Create batch record before staff loading session starts."""

    def add_card_to_carousel(self, reg_number: str, batch_id: str,
                             carousel_slot: int, sms_status: str = "pending") -> bool:
        """Assign card to carousel slot and track SMS status."""

    def mark_card_collected(self, reg_number: str) -> bool:
        """Update card status to 'collected' and log event."""

    def mark_card_rejected(self, reason: str) -> bool:
        """Update card status to 'rejected' (OCR fail, API error, etc.)."""

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        """Retrieve recent audit events for administrator review."""

    def execute_transaction(self, *queries: tuple[str, list]) -> bool:
        """
        Execute multiple SQL queries in atomic transaction.

        Usage:
            db.execute_transaction(
                ("INSERT INTO students ...", [args]),
                ("UPDATE batches ...", [args]),
                ("INSERT INTO audit_log ...", [args])
            )
        """
```

**Transaction Safety**:

- All multi-table writes wrapped in `BEGIN → COMMIT` or `ROLLBACK`
- Corruption guard: UPS ensures clean Pi shutdown (SQLite checkpoint on exit)
- Concurrent access: Only main thread writes; background thread only appends to audit_log

### `ocr.py`

**Purpose**: Image preprocessing and character extraction for ID card registration numbers.

**Pipeline Stages**:

1. **Acquire frame**: CSI camera (triggerred by Conveyor 1 IR) or USB camera (expired slot IR)
2. **Grayscale**: `cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)`
3. **Adaptive threshold**: `cv2.adaptiveGaussianThreshold()` (handles uneven lighting)
4. **Deskew**: Hough line detection → rotation correction
5. **ROI crop**: Extract registration number field (template-matched)
6. **Sharpen**: Contrast enhancement via CLAHE
7. **Tesseract**: `--psm 7 --config alphanumeric-whitelist`

**Public Interface**:

```python
class OCREngine:
    def __init__(self, tesseract_config: str = "--psm 7", confidence_threshold: float = 0.95):
        pass

    def process_frame(self, image: np.ndarray) -> tuple[str | None, float]:
        """
        Process raw camera frame to extracted registration number.

        Args:
            image: BGR frame from camera (numpy array)

        Returns:
            (reg_number, confidence) if extraction succeeds
            (None, 0.0) if below confidence threshold or OCR fails

        Raises:
            OCRTimeoutError: If processing exceeds 5 seconds
        """

    def validate_format(self, reg_number: str) -> bool:
        """
        Validate against university format (regex pattern).
        Example: "T/UDSM/0001/2021" or "T/UDSM/0012/2022"
        """
```

**Error Handling**:

- Low confidence → Servo flap diverts card physically to reject bin (never enters carousel)
- Timeout (>5s) → Card marked as `ocr_timeout`, manual review required
- Format mismatch → Card marked as `ocr_format_invalid`

### `session_manager.py`

**Purpose**: Per-session state machine with explicit lifecycle management.

**State Machine**:

```python
@dataclass
class Session:
    session_id: str
    reg_number: str
    student_name: str
    programme: str
    carousel_slot: int
    auth_factor_1_passed: bool = False  # OTP verified
    auth_factor_2_passed: bool = False  # PIN verified
    session_type: str = "student"       # "student" or "staff"
    created_at: datetime = field(default_factory=datetime.now)

    def clear(self):
        """
        CRITICAL: Called on ALL exit paths (success, cancel, timeout, lockout).
        Resets state to prevent carryover to next session.

        Exit paths:
        - SUCCESS: Card dispensed, SMS sent, session logged
        - CANCEL: User tapped back button, servo releases card/latch
        - TIMEOUT: 90 seconds inactivity, auto-cleared
        - LOCKOUT: 24h PIN lockout or staff PIN wrong × 3
        - ERROR: Network failure, OTP expiry, etc.
        """
```

**Public Interface**:

```python
class SessionManager:
    def __init__(self):
        pass

    def create_session(self, reg_number: str, session_type: str = "student") -> Session:
        """Initialize new session with empty state."""

    def get_current_session(self) -> Session | None:
        """Retrieve active session (returns None if idle)."""

    def clear_session(self):
        """CRITICAL: Explicit teardown called on every exit path."""
```

### `sms_client.py`

**Purpose**: Africa's Talking SMS integration with retry queue.

**Public Interface**:

```python
class SMSClient:
    def __init__(self, api_key: str, sender_name: str):
        pass

    def send_otp_sms(self, phone: str, otp: str, student_name: str = "") -> bool:
        """
        Dispatch OTP to student phone.

        Message template: "Your ID card is ready. OTP: 847291. Collect 24/7."

        Returns True if accepted by SMS gateway (does not guarantee delivery).
        Failed sends queued in SQLite for retry.
        """

    def send_otp_and_pin_sms(self, phone: str, otp: str, temp_pin: str,
                             student_name: str = "") -> bool:
        """
        Dispatch OTP + temporary PIN to first-year student.

        Message template: "OTP: 847291 | Temp PIN: 3829. Change PIN on first visit."
        """

    def retry_failed_sends(self) -> int:
        """
        Background thread entrypoint: Retry SMS sends marked as failed every 15 minutes.
        Returns count of successfully retransmitted messages.
        """
```

**Error Handling**:

- API timeout: Queue in SQLite `batches` table, retry interval 15 minutes
- Invalid phone: Marked as `sms_invalid_phone`, no retry
- Rate limit (Africa's Talking): Exponential backoff
- Network failure: Same as API timeout, automatic retry

### `spi_master.py`

**Purpose**: SPI protocol implementation for hardware command dispatch.

**Frame Format**:

```
Frame Down (Pi → STM32):
  [COMMAND_BYTE (0-255)][PARAMETER_BYTE (0-255)][CHECKSUM_BYTE]

Frame Up (STM32 → Pi):
  [STATUS_BYTE (0=OK, 1=ERR, 2=BUSY)][DATA_BYTE (varies)][CHECKSUM_BYTE]

Checksum: XOR of first two bytes
```

**Commands**:
| Command | Param | Response | Notes |
|---------|-------|----------|-------|
| `0x01` ROTATE_TO_SLOT | Slot index (0–9) | `0x00` OK or `0x01` ERROR | Carousel 36° per slot |
| `0x02` EJECT_CARD | — | `0x00` OK | Servo push at front gate |
| `0x03` UNLOCK_DOOR | — | `0x00` OK | De-energize solenoid (staff) |
| `0x04` LOCK_DOOR | — | `0x00` OK | Energize solenoid |
| `0x05` LATCH_CARD | — | `0x00` OK | Servo clamp (expired slot) |
| `0x06` RELEASE_CARD | — | `0x00` OK | Servo release |
| `0x07` GET_SENSOR_STATE | — | `[status_byte]` | Packed byte: S1|S2|S3|S4|Hall|... |
| `0x08` HOME_CAROUSEL | — | `0x00` OK or `0x01` ERROR | Hall sensor → slot 0 |

**Public Interface**:

```python
class SPIMaster:
    def __init__(self, spi_device: str = "/dev/spidev0.0", speed_hz: int = 1_000_000):
        pass

    def rotate_to_slot(self, slot_index: int) -> tuple[bool, str]:
        """Send ROTATE_TO_SLOT command. Returns (success, message)."""

    def eject_card(self) -> tuple[bool, str]:
        """Send EJECT_CARD command."""

    def unlock_door(self) -> tuple[bool, str]:
        """Send UNLOCK_DOOR command."""

    def get_sensor_state(self) -> tuple[bool, int]:
        """Send GET_SENSOR_STATE. Returns (success, packed_byte)."""

    def home_carousel(self) -> tuple[bool, str]:
        """Send HOME_CAROUSEL (reset step counter to slot 0)."""

    def _send_receive(self, cmd_byte: int, param_byte: int) -> tuple[int, int]:
        """Low-level SPI transaction with checksum."""
```

**Error Handling**:

- STM32 not responding: Timeout exception (SPI stuck, hardware malfunction)
- Checksum mismatch: Invalid response, retry once, escalate if repeated
- Motor timeout (carousel stuck): Return error, lock out further transactions until administrator intervention

### `ui/screens.py`

**Purpose**: Kivy Screen subclasses for all user-facing workflows.

**Screen Classes**:

```python
class IDLEScreen(Screen):
    """Always-visible idle state, awaits staff unlock or student tap."""

class STAFFPINScreen(Screen):
    """PIN entry for staff (3 attempts before 24h lockout)."""

class CHECKLISTScreen(Screen):
    """Pre-batch validation (call staffing checklist)."""

class BATCHScreen(Screen):
    """Live batch loading progress (card count, estimated time, OCR errors)."""

class BATCHSUMMARYScreen(Screen):
    """Batch complete — show totals, SMS status, errors."""

class HOMEScreen(Screen):
    """Student path selector: [OTP Collection] [Expired Card Scan]."""

class OTPINPUTScreen(Screen):
    """6-digit OTP entry with rate-limited resend."""

class PININPUTScreen(Screen):
    """PIN entry (existing or temporary for first-year)."""

class CONFIRMScreen(Screen):
    """Show student info, confirm collection."""

class SUCCESSScreen(Screen):
    """Card dispensed, SMS sent, auto-logout in 30s."""

class LOCKEDScreen(Screen):
    """24h lockout (admin contact info), auto-logout in 60s."""
```

**Event Handlers**:

- Timeout: `on_idle_timeout()` → `session_manager.clear_session()` → Return to IDLE
- Cancel: `on_cancel_button()` → Release servo/latch → Clear session → Return to IDLE
- Success: `on_confirm_button()` → SPI ROTATE + EJECT → Log to audit → Clear session → SUCCESS screen

### `ui/styles.kv`

**Purpose**: Kivy Layout language (.kv file) defining widget tree and event bindings.

**Key Sections**:

- Global font sizes (18px minimum for arm's length readability on 7" screen)
- Color scheme (high contrast for outdoor/bright sunlight)
- Touch event bindings (buttons, text inputs, back swipe)
- Screen transitions (fade, slide)

## Testing

### Unit Tests (`tests/`)

Run all tests:

```bash
cd tests
pytest -v
```

#### `test_auth.py`

- bcrypt hash generation and verification
- OTP generation (6-digit, zero-padded)
- Soft lockout after 3 OTP failures (30 minutes)
- Hard lockout after 3 PIN failures (24 hours, audited)
- PIN change for first-year students

#### `test_ocr.py`

- Preprocessing pipeline (grayscale, threshold, deskew)
- Tesseract extraction with alphanumeric whitelist
- Regex format validation
- Confidence threshold gating (low-confidence cards diverted)
- Timeout handling (>5 seconds)

#### `test_spi.py`

- Frame encoding/decoding
- Checksum calculation (XOR)
- Command dispatch to mock STM32 via loopback

### Integration Tests

```bash
# Mock API running with sample data
python ../mock-db-api/app.py &

# Run full workflow simulation
pytest tests/test_integration.py -v
```

**Test Scenarios**:

- Staff PIN login → Batch loading → Card OCR → API fetch → SMS dispatch → Carousel rotation
- Student OTP entry → PIN verification → Carousel slot collection → Success
- Lockout escalation: 3× PIN fail → 24h lockout → Audit log → Admin notification

## Logging & Monitoring

### Application Logs

```
/home/pi/card-issuance-system/kiosk-brain/data/logs/
├── kiosk_YYYY-MM-DD.log       # Daily application logs
├── ocr_YYYY-MM-DD.log         # OCR pipeline diagnostics
└── spi_YYYY-MM-DD.log         # SPI command trace
```

### Audit Log (SQLite)

```sql
SELECT * FROM audit_log
WHERE timestamp > datetime('now', '-1 day')
ORDER BY timestamp DESC;
```

**Event Types**:

- `session_start`: Student or staff initiates session
- `otp_sent`: SMS dispatched successfully
- `otp_verify_fail`: Incorrect OTP (with attempt count)
- `pin_verify_fail`: Incorrect PIN (with attempt count)
- `otp_lockout`: 3 OTP failures → 30-min cooldown
- `pin_lockout`: 3 PIN failures → 24h lockout (escalated to admin)
- `collection_success`: Card dispensed successfully
- `card_rejected_ocr`: OCR confidence below threshold

## Performance Tuning

| Component          | Bottleneck                                   | Mitigation                                            |
| ------------------ | -------------------------------------------- | ----------------------------------------------------- |
| **OCR**            | Tesseract processing (1–3 seconds per frame) | Pre-process image quality, ROI tuning                 |
| **API call**       | Network latency (mDNS lookup + HTTPS)        | Connection pooling, keep-alive                        |
| **SMS dispatch**   | Africa's Talking rate limit                  | Queue failures, background retry                      |
| **SPI latency**    | Motor response time                          | Increase SPI clock (1 MHz → 2 MHz if STM32 tolerates) |
| **Kivy rendering** | GPU fill rate on 7" display                  | Reduce animation frame count, optimize .kv layouts    |

## Troubleshooting

### Common Issues

| Issue                                         | Cause                         | Solution                                                   |
| --------------------------------------------- | ----------------------------- | ---------------------------------------------------------- |
| **Pi cannot reach university-db.local**       | mDNS not resolved             | Check avahi-daemon running on mock API laptop              |
| **OCR accuracy very low**                     | Poor card lighting            | Adjust conveyor LED brightness, check ROI crop bounds      |
| **SPI timeout (motor stuck)**                 | STM32 firmware crash          | Check ST-Link debugger logs, reload firmware               |
| **Kivy display corruption**                   | GPU memory exhaustion         | Reduce concurrent animations, check DSI ribbon connection  |
| **SMS not dispatched**                        | Invalid API key or rate limit | Check config.py, monitor audit log for `sms_failed` status |
| **Database file corruption after power loss** | Incomplete checkpoint         | Verify UPS backup working (5V rail hold time)              |

## Deployment Checklist

- [ ] Python 3.11 and dependencies installed
- [ ] Database initialized (`python db/init_db.py`)
- [ ] Africa's Talking API key loaded in config.py
- [ ] University database mDNS name resolvable
- [ ] Staff PIN hashed in config.py (never plaintext)
- [ ] Kivy runs on framebuffer (DSI display intact)
- [ ] SPI communication verified (GPIO connected to STM32)
- [ ] Systemd service enabled for autostart
- [ ] Camera calibration (CSI focus, USB angle)
- [ ] Test batch with sample cards
- [ ] Test student OTP/PIN workflows

## References

- **Kivy Documentation**: https://kivy.org/doc/
- **OpenCV API**: https://docs.opencv.org/
- **Tesseract OCR**: https://github.com/UB-Mannheim/tesseract/wiki
- **Africa's Talking SDK**: https://africastalking.com/sms/api
- **SQLite**: https://www.sqlite.org/
- **Python spidev**: https://github.com/doceme/py-spidev
