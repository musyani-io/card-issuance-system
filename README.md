# Smart ID Card Distribution Kiosk

## Overview

A distributed embedded system for autonomous ID card issuance in university environments. The system combines a Raspberry Pi 5 (4GB) application controller with an STM32 Nucleo-F401RE hardware control unit, interfaced via SPI over a multi-stage card transport mechanism. The kiosk supports batch card loading by staff and individual card collection by students with two-factor authentication (OTP + PIN).

## System Architecture

The kiosk consists of three major subsystems:

### 1. Raspberry Pi 5 (4GB) (Application Tier)

- **OS**: Raspberry Pi OS Lite (headless)
- **Runtime**: Python 3.11
- **UI Framework**: Kivy GPU-accelerated rendering on framebuffer
- **Display**: Official 7" DSI touchscreen (800 × 480 px)
- **Responsibilities**:
  - Touchscreen UI (staff PIN login, student OTP/PIN entry, batch progress monitoring)
  - OCR pipeline (camera frame preprocessing via OpenCV, character extraction via Tesseract 5)
  - HTTPS API communication with university database
  - SMS dispatch via Africa's Talking API
  - SQLite database persistence
  - SPI master protocol (initiates all hardware commands)
  - Session state management with explicit cleanup
  - Audit logging (all authentication events, lockouts, session traces)

### 2. STM32 Nucleo-F401RE (Hardware Control Tier)

- **MCU**: ARM Cortex-M4 @ 84 MHz
- **Development**: C with STM32 HAL library (STM32CubeIDE)
- **Interface**: SPI slave mode (receives commands from Pi)
- **Responsibilities**:
  - Stepper motor pulse generation (NEMA 17 × 2) via HAL timers at precise frequencies
  - Servo PWM control (SG90 × 2) at 50 Hz
  - Solenoid electromagnetic lock control via MOSFET driver
  - Sensor state polling (IR break-beams × 4, Hall-effect absolute home reference)
  - Hardware interlock: door-open IR sensor → GPIO interrupt handler disables all motor step outputs (cannot be overridden from Pi)
  - Motor current limiting via A4988 driver potentiometer calibration

### 3. Mechanical Subsystems

- **Turntable Carousel**: 10-slot disc, GT2 belt drive, neodymium card retention
- **Conveyor 1**: Input card transport from staff tray to turntable rear gate
- **CSI Camera Station**: Fixed mount above Conveyor 1 for batch card OCR
- **Expired Card Scanner**: USB camera in front-panel slot with servo latch (for returning student verification)
- **Card Ejector**: SG90 servo flap at turntable front gate (student collection point)
- **Staff Door Lock**: 12V solenoid with fail-secure design (locked on power loss)

## Development Phases

| Phase | Duration  | Focus                                                                                                                        |
| ----- | --------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **1** | Weeks 1–2 | OCR pipeline (OpenCV preprocessing, Tesseract validation, regex matching)                                                    |
| **2** | Weeks 2–3 | Database schema (SQLite), mock university API (Flask, mDNS discovery)                                                        |
| **3** | Weeks 3–4 | Authentication (bcrypt hashing, 6-digit OTP generation, 4–6 digit PIN lockout logic), SMS integration (Africa's Talking)     |
| **4** | Weeks 4–5 | Kivy touch UI (ScreenManager, SessionManager state machine), SPI protocol definition and Pi-side client                      |
| **5** | Weeks 5–7 | STM32 HAL firmware, mechanical prototype (acrylic or 3D-printed carousel), sensor integration, end-to-end system integration |

## Directory Structure

```bash
card-issuance-system/
├── README.md                          # This file
├── BUILD.md                           # Build and deployment instructions
├── docs/
│   ├── kiosk_architecture.html        # Interactive system architecture diagram
│   ├── official/                       # Official documentation (university APIs, compliance)
│   └── primary/                        # Design rationale and technical specifications
├── kiosk-brain/                        # Raspberry Pi Python application
│   ├── main.py                         # Entry point (Kivy app initialization)
│   ├── config.py                       # Configuration (API keys, timeouts, paths)
│   ├── requirements.txt                # Python dependencies
│   ├── README.md                       # Kiosk-brain subsystem documentation
│   ├── modules/
│   │   ├── api_client.py              # HTTPS university API wrapper
│   │   ├── auth.py                    # OTP/PIN verification (bcrypt, lockout logic)
│   │   ├── database.py                # SQLite interface (schema queries, transactions)
│   │   ├── ocr.py                     # OpenCV + Tesseract image processing
│   │   ├── session_manager.py         # Per-session state lifecycle
│   │   ├── sms_client.py              # Africa's Talking SDK wrapper
│   │   └── spi_master.py              # SPI command protocol (frame format, checksum)
│   ├── ui/
│   │   ├── screens.py                 # Kivy Screen subclasses (IDLE, STAFF_PIN, etc.)
│   │   └── styles.kv                  # Kivy layout definitions (KivyLang DSL)
│   ├── tests/
│   │   ├── test_auth.py               # Unit tests (bcrypt, OTP validation)
│   │   ├── test_ocr.py                # OCR pipeline regression tests
│   │   ├── test_spi.py                # SPI frame encoding/decoding
│   │   └── sample_cards/              # JPEG cards for OCR testing
│   ├── db/
│   │   ├── schema.sql                 # SQLite DDL (students, auth, audit_log tables)
│   │   ├── init_db.py                 # Database initialization script
│   │   └── migrations/                # Schema version control
│   └── data/
│       └── logs/                      # Application logs (audit trail)
├── mock-db-api/                        # Flask development API (university DB mock)
│   ├── app.py                          # Flask app (single /students/{reg_number} endpoint)
│   ├── config.py                       # API key, student fixture data
│   ├── requirements.txt                # Python dependencies
│   └── README.md                       # Mock API documentation
└── firmware/                           # STM32 firmware (managed separately)
    └── STM32CubeIDE project          # C, HAL, SPI slave mode, motor control
```

## Network Architecture

### WiFi / mDNS Layer

- **Raspberry Pi ↔ Mock University DB**: HTTPS over WiFi/mobile hotspot, service discovery via mDNS
  - Pi resolves `university-db.local` automatically (no hardcoded IP)
  - Supported on both shared WiFi networks and mobile hotspot failover

### API Integration Points

1. **University Database API** (external)
   - Endpoint: `GET /students/{reg_number}`
   - Response: `{ "name": "...", "programme": "...", "phone": "+...", "status": "active|inactive|suspended" }`
   - Timeout: 5 seconds per request
   - Retries: 3 with exponential backoff
   - Auth: Bearer token in HTTP header

2. **Africa's Talking SMS Gateway** (external)
   - Method: HTTP POST `/message/send`
   - Credentials: API key and sender name stored in `config.py`
   - Supported: Returning student OTP, first-year OTP + temporary PIN
   - Retry queue: Failed sends queued in SQLite `batches` table, background thread retries every 15 minutes

### SPI Protocol (Pi Master ↔ STM32 Slave)

- **Frame Format**: `[COMMAND_BYTE][PARAMETER_BYTE][CHECKSUM]` (Pi → STM32)
- **Response**: `[STATUS_BYTE][DATA_BYTE][CHECKSUM]` (STM32 → Pi)
- **Commands**:
  - `ROTATE_TO_SLOT(slot_index)` — Rotate carousel to target slot
  - `EJECT_CARD()` — Push card through front-gate ejector servo
  - `UNLOCK_DOOR()` — De-energize solenoid lock
  - `LOCK_DOOR()` — Energize solenoid lock
  - `LATCH_CARD()` / `RELEASE_CARD()` — Expired slot servo control
  - `GET_SENSOR_STATE()` — Read all 5 sensor states (packed byte)
  - `HOME_CAROUSEL()` — Rotate until hall-effect sensor triggers, reset step counter to zero
- **Safety**: Pi crash → STM32 receives no commands → all motors remain stopped

## Database Schema

SQLite file stored on 64GB microSD at runtime. Three critical tables:

### `students` Table

```sql
CREATE TABLE students (
  reg_number TEXT PRIMARY KEY,
  first_name TEXT NOT NULL,
  surname TEXT NOT NULL,
  programme TEXT,
  phone TEXT,
  status TEXT CHECK(status IN ('active', 'inactive', 'suspended')),
  added_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### `authentication` Table

```sql
CREATE TABLE authentication (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reg_number TEXT NOT NULL FOREIGN KEY REFERENCES students(reg_number),
  otp_hash TEXT,
  otp_expiry DATETIME,
  pin_hash TEXT,
  pin_attempts_today INTEGER DEFAULT 0,
  pin_lockout_until DATETIME,
  created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### `audit_log` Table

```sql
CREATE TABLE audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reg_number TEXT,
  event_type TEXT CHECK(event_type IN ('session_start', 'otp_sent', 'otp_verify_fail', 'pin_verify_fail', 'otp_lockout', 'pin_lockout', 'pin_lockout_admin_review', 'collection_success', 'card_rejected_ocr')),
  details TEXT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

Automated cleanup: Background cron job purges `students` records older than 120 days every four months (prevents carousel slot index exhaustion).

## Power Architecture

- **Primary Rail (12V, 10A)**: Motors, motor drivers, solenoid lock
- **Logic Rail (5V, regulated)**: Raspberry Pi, display, STM32 logic, servo control
- **Power Separation**: Motors on 12V rail, logic on 5V buck-converted rail (prevents stepper switching noise corruption of Pi microSD)
- \*\*UPS (5V): Backup Li-ion cell provides 5–10 minutes runtime (Pi + display + STM32 only, not motors)
  - Ensures SQLite database closure on mains failure before battery depletion
  - Motors stop cleanly (no backup power) — mechanically safe

## Sensors

| Sensor      | Type        | Purpose                                   | Position                        |
| ----------- | ----------- | ----------------------------------------- | ------------------------------- |
| IR Sensor 1 | Break-beam  | Staff door open detection                 | Door frame                      |
| IR Sensor 2 | Break-beam  | Rear gate card detection                  | Turntable rear gate             |
| IR Sensor 3 | Break-beam  | Front gate card eject confirmation        | Turntable front gate            |
| IR Sensor 4 | Break-beam  | Expired card slot insertion               | Front panel expired slot        |
| Hall A3144  | Hall-effect | Carousel absolute home (slot 0 reference) | Turntable frame + magnet on rim |

## Hardware Bill of Materials (BOM)

| Component                   | Qty       | Notes                                             |
| --------------------------- | --------- | ------------------------------------------------- |
| Raspberry Pi 5 (4GB RAM)    | 1         | SoM: BCM2712, 64-bit ARMv8 @ 2.4 GHz              |
| Official 7" DSI Touchscreen | 1         | 800 × 480, DSI ribbon                             |
| STM32 Nucleo-F401RE         | 1         | Breakout board, 84 MHz Cortex-M4                  |
| Pi Camera Module v2 (CSI)   | 1         | 8 MP Sony IMX219, fixed mount over Conveyor 1     |
| USB Webcam (720p)           | 1         | Inside front-panel expired card slot              |
| NEMA 17 Stepper Motor       | 2         | Turntable drive + Conveyor 1 drive                |
| A4988 Stepper Driver        | 2         | Microstepping to 1/8, current-limit potentiometer |
| SG90 Servo Motor            | 2         | Expired slot latch + front-gate ejector           |
| 12V Solenoid Lock           | 1         | Fail-secure (energized = locked)                  |
| IRLZ44N MOSFET              | 1         | 12V solenoid gate driver                          |
| IR Break-Beam Sensor Module | 4         | Digital output on GPIO                            |
| A3144 Hall-Effect Sensor    | 1         | Carousel absolute home                            |
| GT2 Timing Belt + Pulleys   | As needed | Stepper coupling to drives                        |
| 10-Slot Turntable Carousel  | 1         | Acrylic prototype or 3D-printed                   |
| 12V/10A Switching PSU       | 1         | Mains 220–240V input                              |
| 12V→5V Buck Converter (3A)  | 1         | Logic rail regulation                             |
| 5V UPS Li-ion Module        | 1         | Backup for Pi shutdown                            |
| Neodymium Disc Magnets      | 10        | Card retention per slot                           |
| 64GB Class 10 microSD Card  | 1         | OS, Python env, SQLite DB file                    |

## Authentication Flow

### Two-Factor Process

**Factor 1: OTP (One-Time Passcode)**

1. Student enters registration number
2. Pi queries university API → fetches phone number
3. Pi generates 6-digit OTP via `secrets.randbelow(1_000_000)` (zero-padded)
4. OTP stored as bcrypt hash in SQLite `authentication` table with 24-hour expiry
5. SMS sent via Africa's Talking with OTP and collection instructions
6. Student receives SMS with OTP (or retransmit with rate limit 1× per 10 minutes)
7. Student enters 6-digit OTP on touchscreen
8. Pi queries SQLite → validates hash and expiry
9. **Soft lockout**: 3 consecutive OTP failures → 30-minute cooldown

**Factor 2: PIN (Personal Identification Number)**

1. For **returning students**: Existing PIN demanded (4–6 digits, bcrypt verified)
2. For **first-year students**: Temporary PIN received in SMS, must set permanent PIN on first collection visit
3. **Lockout policy**: 3 consecutive PIN failures → 24-hour hard lockout (flagged in audit log for administrator review)
4. On success: Card slot assignment, SMS acknowledgment

### Session State Machine (Kivy ScreenManager)

```
IDLE (student tap or staff unlock)
 ├─→ STAFF_PIN (if staff unlock triggered)
 │    ├─ [PIN correct] → CHECKLIST (staff batch loading)
 │    └─ [PIN incorrect × 3] → LOCKED (24h lockout)
 │
 └─→ HOME (student path selection)
      ├–→ [OTP path]
      │    ├─ OTP SCREEN → [OTP correct]
      │    ├─ PIN SCREEN (existing or temp) → [PIN correct]
      │    └─ CONFIRM SCREEN → [confirm] → SUCCESS → IDLE
      │
      └─→ [Expired card + camera scan]
           ├─ Servo latch active, camera acquires frame
           ├─ OCR extracts reg number, validates format
           └─ [Reg found] → OTP SCREEN (as above)
```

## OCR Pipeline

1. **Image Acquisition**
   - CSI camera: Frame buffered on Pi Camera v2 arrival (conveyor motion IR trigger)
   - USB camera: Frame captured on expired-slot IR sensor activation

2. **Preprocessing** (OpenCV)
   - Grayscale conversion
   - Adaptive Gaussian thresholding (handles uneven card lighting)
   - Deskew via Hough line angle detection
   - ROI cropping to registration number field
   - Contrast enhancement and sharpening

3. **Character Extraction** (Tesseract 5)
   - Single-line mode (`--psm 7`)
   - Alphanumeric character whitelist (eliminates spurious symbols)
   - Configurable language model

4. **Validation** (Regex + Confidence)
   - Regex against university format (e.g., `T/UDSM/0001/2021`)
   - Confidence threshold gate (tunable, default 95%)
   - **Low-confidence diversion**: Servo flap routes low-confidence cards to reject bin (never carousel entry)

## Installation & Setup

### Raspberry Pi 4B

1. **OS Installation**

   ```bash
   # Flash Raspberry Pi OS Lite to microSD via Raspberry Pi Imager
   # SSH into Pi: ssh pi@raspberry.local
   ```

2. **Python Environment**

   ```bash
   sudo apt update
   sudo apt install -y python3.11 python3.11-venv python3-pip
   sudo apt install -y libopencv-dev tesseract-ocr python3-opencv

   cd /home/pi/card-issuance-system/kiosk-brain
   python3.11 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   ```

3. **Database Initialization**

   ```bash
   cd db
   python init_db.py         # Creates SQLite file with schema
   ```

4. **Configuration**
   - Edit `config.py`:
     - API key for Africa's Talking SMS
     - University API base URL (resolved via mDNS: `university-db.local`)
     - OTP/PIN policy parameters (lockout durations, retry limits)

5. **Autostart Service** (systemd)
   - Create `/etc/systemd/system/kiosk.service`:

     ```ini
     [Unit]
     Description=Smart ID Kiosk Brain
     After=network-online.target

     [Service]
     Type=simple
     User=pi
     WorkingDirectory=/home/pi/card-issuance-system/kiosk-brain
     ExecStart=/home/pi/card-issuance-system/kiosk-brain/venv/bin/python main.py
     Restart=on-failure
     RestartSec=10

     [Install]
     WantedBy=multi-user.target
     ```

   - Enable: `sudo systemctl enable kiosk.service`

### STM32 Firmware

1. **Development Environment**
   - Install STM32CubeIDE (free, Linux-native)
   - Import HAL support for STM32F4 family

2. **Configuration**
   - SPI1 slave mode with interrupt handler
   - TIM2/TIM3 for stepper pulse generation (frequency configurable)
   - TIM4 for servo 50 Hz PWM
   - GPIO interrupt for door-open IR sensor (priority: disables motor steps)

3. **Compile & Flash**

   ```bash
   # Build project in STM32CubeIDE, then flash via ST-Link programmer
   ```

### Mock University API

1. **Installation** (on development laptop)

   ```bash
   cd mock-db-api
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run with mDNS Publishing**

   ```bash
   # Install avahi for mDNS advertising
   sudo apt install avahi-daemon

   # Launch Flask app with mDNS name resolution
   python app.py --mdns-advertise
   # Resolves as: university-db.local:5000
   ```

## Testing

### Unit Tests

```bash
cd kiosk-brain/tests
pytest test_auth.py       # bcrypt hashing, OTP validation, lockout logic
pytest test_ocr.py        # OCR pipeline regression (sample_cards/*.jpg)
pytest test_spi.py        # SPI frame encoding/decoding, checksum verification
```

### Integration Tests

- **Mock API**: `pytest` fixtures with sample student records
- **Database**: Transactional rollback per test (no pollution)
- **SMS**: Africa's Talking sandbox account (free, no cost)

## Performance Targets

| Metric                      | Target                                   | Notes                                                |
| --------------------------- | ---------------------------------------- | ---------------------------------------------------- |
| **Card throughput**         | 10–15 cards/min (batch)                  | Conveyor speed + carousel rotation + servo actuation |
| **OCR accuracy**            | 98%+ (well-lit card)                     | Tesseract v5 + regex validation + confidence gating  |
| **Pi startup**              | <30 seconds                              | OS boot + Kivy framebuffer init on DSI display       |
| **SPI command latency**     | <10 ms                                   | Motor motion imperceptible to user                   |
| **Authentication response** | <2 seconds (local), <5 seconds (network) | SQLite lookup vs. API round-trip                     |
| **SMS delivery**            | <60 seconds                              | Africa's Talking typical delivery window             |

## Known Limitations & Future Roadmap

### Phase Release 1 (Current)

- **SPI**: Unencrypted frame transport (trusted local network only)
- **OCR**: Assumes uniform diffuse lighting (field lighting in production location critical)
- **Carousel**: 10-slot prototype (expandable to 20-slot via firmware)
- **Mobile**: Python 3.11, Kivy 2.3.1 (ARM64 native on Pi OS)

### Phase Release 2 (Q4 2026)

- SPI frame encryption (optional, based on security review)
- Multilingual OCR (Swahili, French, Arabic character sets)
- Network failover SMS via backup provider (Twilio fallback)
- Wireless firmware update mechanism (over-the-air STM32 flashing)

### Phase Release 3 (TBD)

- Biometric fingerprint scanner integration (optional 2FA)
- Card printer integration (on-site ID photo printing)
- Physical security: encrypted tamper-detection switches on access panels

## License

[Specify license here — e.g., MIT, GPL-3.0]

## References

- **OpenCV Documentation**: <https://docs.opencv.org/>
- **Tesseract OCR**: <https://github.com/UB-Mannheim/tesseract/wiki>
- **Kivy Framework**: <https://kivy.org/doc/>
- **Africa's Talking SMS**: <https://africastalking.com/sms/api>
- **SQLite**: <https://www.sqlite.org/lang.html>
- **STM32 HAL Reference**: <https://www.st.com/resource/en/reference_manual/dm00031020-stm32f446xx-advanced-arm-based-32-bit-mcus-stm32f4-series-reference-manual-stmicroelectronics.pdf>
