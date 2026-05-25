# Smart ID Card Distribution Kiosk

## Overview

A distributed embedded system for autonomous ID card issuance in university environments. The system combines:

- **Raspberry Pi 5 (4GB)**: Python application tier with Kivy touchscreen UI
- **STM32 Nucleo-F401RE**: Hardware control tier via SPI communication
- **Multi-stage Transport**: Card carousel, conveyor, OCR, and dispensing mechanisms

**Core Features**: Batch card loading (staff) | Student card collection | Two-factor authentication (OTP + PIN) | OCR registration number extraction | Immutable audit logging

## System Architecture

### Computing Tiers

**Raspberry Pi 5 (Application Controller)**

- Python 3.11 runtime with Kivy 2.3.1 touch UI framework
- 7" DSI touchscreen interface (800×400 resolution, landscape-only)
- OCR pipeline (OpenCV + Tesseract 5) for batch card scanning
- SQLite database with immutable audit logs
- SPI master (1 MHz, 3-byte frames) to STM32 for motor/sensor control
- HTTPS API client for university database (mDNS discovery: `university-db.local`)
- SMS dispatch via BRIQ Solutions REST API (Tanzania)

**STM32 Nucleo-F401RE (Hardware Control)**

- SPI slave mode (1 MHz, responds to 3-byte frame format)
- Motor control: 2× NEMA 17 stepper motors via A4988 drivers (carousel, conveyor)
- Servo control: 2× SG90 servos via PWM (card ejection, expired-card latch)
- Solenoid lock control: 12V energized-to-lock (fail-secure on power loss)
- Sensor polling: 4× IR break-beam sensors, 1× Hall-effect sensor (absolute homing)
- Hardware watchdog: Door-open IR → automatic motor disable (failsafe)

### Mechanical Subsystems

- **Turntable Carousel**: 10-slot disc with neodymium magnets for passive card retention; step-indexed by stepper motor; expandable to 20-slot with firmware changes
- **Conveyor Systems**: Input transport (staff tray → carousel rear gate) + Output (carousel front → student collection point); both driven by NEMA 17 steppers
- **Scan Station**: CSI camera mounted above Conveyor 1 for batch OCR; USB camera in front panel for expired-card registration verification
- **Card Dispensing**: SG90 servo pushes card from carousel front gate to ejection point
- **Security**: 12V solenoid lock on staff access door; energized-to-lock design (fails secure on power loss)

## Development Phases

| Phase | Duration  | Focus                                                                                                                        | Status |
| ----- | --------- | ---------------------------------------------------------------------------------------------------------------------------- | ------ |
| **1** | Weeks 1–2 | OCR pipeline (OpenCV preprocessing, Tesseract validation, regex matching) — *using phone images for rapid development*        | ▯ 10%  |
| **2** | Weeks 2–3 | Database schema (SQLite), mock university API (Flask, mDNS discovery)                                                        | ▰ 90%  |
| **3** | Weeks 3–4 | Authentication (bcrypt hashing, 6-digit OTP generation, 4–6 digit PIN lockout logic), SMS integration (BRIQ Solutions)       | ▰ 100% |
| **4** | Weeks 4–5 | Kivy touch UI (ScreenManager, SessionManager state machine), SPI protocol definition and Pi-side client                      | ▰ 95%  |
| **5** | Weeks 5–7 | STM32 HAL firmware, mechanical prototype (acrylic or 3D-printed carousel), sensor integration, end-to-end system integration | ▯ 0%   |
| **6** | Week 8    | Enclosure, integration testing, documentation                                                                                | ▯ 0%   |

## Directory Structure

```
card-issuance-system/
├── README.md                      # This file
├── BUILD.md                       # Project phases & current progress tracking
├── docs/                          # Architecture diagrams & documentation
│   ├── kiosk_architecture.html    # State machine flow diagrams (HTML interactive)
│   ├── carousel_3d_v2.html        # 3D carousel design visualization
│   └── business/official/         # Business requirements & formal specs
├── kiosk_brain/                   # Raspberry Pi 5 Python application (main system)
│   ├── main.py                    # Kivy app entry point, ScreenManager init
│   ├── config.py                  # Environment variables, API keys, timeouts
│   ├── requirements.txt           # Python 3.11 dependencies
│   ├── README.md                  # Subsystem architecture & module overview
│   ├── SPI_PROTOCOL.md            # 3-byte SPI frame format specification
│   ├── modules/                   # Core business logic packages
│   │   ├── main.py / __init__.py
│   │   ├── api_client.py          # HTTPS university DB client (mDNS discovery)
│   │   ├── auth.py                # OTP/PIN generation, bcrypt validation
│   │   ├── database.py            # SQLite schema, transactions, queries
│   │   ├── ocr.py                 # OpenCV preprocessing, Tesseract integration
│   │   ├── session_manager.py     # Per-session state lifecycle
│   │   ├── sms_client.py          # BRIQ SMS API wrapper
│   │   └── spi_master.py          # SPI frame encoding, checksum, dispatch
│   ├── ui/                        # Kivy GUI screens and styling
│   │   ├── screens.py             # Screen subclasses (WELCOME, OTP, PIN, CONFIRM, etc.)
│   │   ├── styled_widgets.py      # Custom Kivy widgets (buttons, text inputs)
│   │   ├── styles.kv              # Kivy DSL: layouts, event bindings
│   │   └── constants.py           # UI constants (colors, timeouts, screen names)
│   ├── tests/                     # Unit & integration tests
│   │   ├── test_auth.py           # Bcrypt, OTP generation, lockout logic
│   │   ├── test_ocr.py            # Image preprocessing, Tesseract mocking
│   │   └── test_spi.py            # SPI frame encoding, checksum validation
│   └── db/                        # Database schema & initialization
│       ├── schema.sql             # SQLite DDL (students, cards, auth, audit_log, batches)
│       ├── init_db.py             # Database initialization script
│       └── DATABASE_DESIGN.md     # Schema design rationale and constraints
├── mock_db_api/                   # Flask mock university API (development only)
│   ├── app.py                     # Flask entry point, /students/{reg_number} endpoint
│   ├── README.md                  # Mock API usage instructions
│   └── requirements.txt           # Flask, SSL, mDNS dependencies
├── firmware/                      # STM32 Nucleo-F401RE embedded C code
│   ├── BUILD.md                   # Firmware build and flashing instructions
│   ├── pin_assignment.txt         # STM32 GPIO mapping (motors, sensors, SPI)
│   └── real_time_controller/      # STM32CubeIDE project
│       ├── real_time_controller.ioc  # CubeMX hardware configuration
│       ├── STM32F401RETX_FLASH.ld    # Linker script
│       ├── Inc/
│       │   ├── main.h
│       │   ├── stm32f4xx_hal_conf.h
│       │   └── stm32f4xx_it.h
│       ├── Src/
│       │   ├── main.c             # Firmware entry point, SPI ISR loop
│       │   ├── system_stm32f4xx.c
│       │   └── syscalls.c
│       ├── Startup/
│       │   └── startup_stm32f401retx.s  # ARM Cortex-M4 bootstrap
│       ├── Drivers/               # CMSIS-CORE, STM32F4 HAL
│       └── datasheets/            # Component datasheets (A4988, motors, sensors)
└── hardware/                      # Hardware design & schematics
    ├── README.md                  # Power distribution, motor control architecture
    ├── BUILD.md                   # Hardware assembly & testing instructions
    ├── kiCAD/                     # KiCAD PCB design (development)
    │   ├── rev_polarity_prot.kicad_pro
    │   ├── rev_polarity_prot.kicad_sch
    │   └── rev_polarity_prot.kicad_pcb
    ├── Altium/                    # Altium Designer schematics (learning/reference)
    │   └── rev_polarity_protection/
    ├── simulations/               # SPICE simulations (Proteus)
    │   └── rev_polarity_protection.pdsprj
    └── datasheets/                # Component reference documents (motors, drivers, PSU)
```

## Architecture Details

### Network Communication

**Pi ↔ University Database**: HTTPS + mDNS (development mode auto-discovers `university-db.local`)

- Endpoint: `GET /students/{reg_number}` with Bearer token authentication
- Timeout: 5 seconds with 3× exponential backoff retry
- Supports WiFi and mobile hotspot failover
- Falls back to local SQLite cache if API unavailable

**Pi ↔ SMS Gateway**: HTTPS POST to BRIQ Solutions (Tanzania)

- Endpoint: `POST /v1/message/send-instant`
- Authentication: API key + sender ID in `config.py`
- Retry queue: Failed sends stored in SQLite, background retry every 15 min
- Supports both OTP and custom PIN messages

**Pi ↔ STM32**: SPI serial communication (1 MHz, local link only)

- Frame format: [COMMAND (1B)][PARAMETER (1B)][CHECKSUM (1B)]
- Commands: Carousel rotation, card ejection, lock/unlock, sensor polling, homing
- Safety: Pi crash → STM32 receives no commands → all motors remain stopped (no runaway)

### Authentication & Sessions

**Two-Factor Authentication**

- **Factor 1 (OTP)**: 6-digit code generated via Python `secrets` module, bcrypt-hashed in DB, 24h expiry
  - Sent via SMS (BRIQ) + Email (optional future enhancement)
  - 3 consecutive failures → 30-min soft lockout (user can retry after cooldown)
- **Factor 2 (PIN)**: 4–6 digits; bcrypt-hashed in database
  - Returning students use existing PIN
  - First-year students receive temporary PIN in SMS, must verify and create permanent PIN
  - 3 consecutive failures → 24-hour hard lockout (flagged for administrator review)

**Session Management**

- Per-transaction state tracked in volatile `SessionManager` Python object (in-memory, not persistent)
- Explicit cleanup on transaction completion or 5-min timeout (prevents card hijacking)
- SessionManager methods: `initialize()`, `set_otp_valid()`, `set_pin_valid()`, `teardown()`
- All events logged to immutable `audit_log` table (registration number, event type, timestamp, session ID)

### Database

**SQLite schema** (5 tables, no external dependencies) includes:

- `students`: Registration number (PK), first/surname, email, phone, programme, status
- `authentication`: OTP hash, PIN hash, is_temp_pin flag, failed attempt counters, lockout expiry
- `cards`: Card ID, registration number (FK), slot index, batch reference, status, timestamps
- `audit_log`: Immutable append-only log (registration number, event type, failure reason, session ID, timestamp)
- `batches`: Batch metadata, card counts, staff ID, scan timestamp

**Consistency**: All tables use TIMESTAMP for sorting; registration_number is the natural foreign key linking students, authentication, and cards. No cascading deletes (soft deletes via status field instead).

**Performance**: Indexed on registration_number and audit_log.event_time for fast queries; SQLite sufficient for single-instance kiosk (no concurrency)

### Power Architecture

**Three-rail isolation strategy** (prevents motor noise coupling into Pi logic):

| Rail       | Voltage | Current | Components                              | Protection                        |
| ---------- | ------- | ------- | --------------------------------------- | --------------------------------- |
| Primary    | 12V     | 10A     | NEMA 17 motors, A4988 drivers, solenoid | 12A fuse, separate ground plane   |
| Logic      | 5V      | 3A      | Raspberry Pi, display, STM32, servos    | 3A buck converter, TVS diode      |
| Backup UPS | 5V      | 1A      | Pi + display + STM32 emergency runtime  | Ideal diode, automatic switchover |

**Topology**:

- Single 12V/10A switching PSU (mains input 220–240V AC)
- 12V→5V buck converter with LC filtering (1000µF + 100nF capacitors) feeds logic rail
- 5V Li-ion UPS module with ideal diode provides seamless switchover on mains loss
- Star ground connection at PSU negative terminal only (minimizes ground loops)
- Main 12A fuse on 12V rail; 3A fused outputs to motor drivers, solenoid, and servo rails

**Failsafe behavior**:

- On mains loss: UPS supplies ~5–10 min runtime (Pi + display + STM32 only, motors stop immediately)
- Ensures SQLite database closes cleanly; motors fail-safe (no backup power for motion)
- Door solenoid is energized-to-lock (loses power → lock engages, fail-secure)

### Sensors

| Sensor | Type        | GPIO (STM32)   | Purpose                                             | Active Mode |
| ------ | ----------- | -------------- | --------------------------------------------------- | ----------- |
| IR1    | Break-beam  | PB4            | Staff door open detection (hardwired interrupt)     | Low         |
| IR2    | Break-beam  | PB5            | Rear gate card detection (carousel loading check)   | Low         |
| IR3    | Break-beam  | PB6            | Front gate card ejection confirmation (dispensing)  | Low         |
| IR4    | Break-beam  | PB7            | Expired card slot insertion detection               | Low         |
| Hall A | Hall-effect | PA11 (PULL_UP) | Carousel absolute home reference (slot 0 detection) | Low         |

All inputs use internal pull-ups; firmware polls every 10ms or uses GPIO edge interrupts for critical signals (door open)

### Bill of Materials (Key Components)

- **Compute**: Raspberry Pi 5 (4GB), STM32 Nucleo-F401RE
- **Display**: Official 7" DSI touchscreen (800×480, now 800×400 landscape-only)
- **Cameras**: Pi Camera Module v2 (CSI for batch scan), USB 720p webcam (expired card slot)
- **Motors & Actuation**:
  - NEMA 17 stepper motors (×2): Carousel, Conveyor 1
  - SG90 micro servos (×2): Card ejection flap, expired-card latch
  - A4988 stepper drivers (×2, 12V logic)
  - IRLZ44N MOSFET (solenoid switch, logic-level gate)
- **Sensing**: IR break-beam sensors (×4, 5V), A3144 Hall-effect sensor (carousel homing)
- **Security**: 12V solenoid lock (energized-to-lock, normally closed when de-energized)
- **Power Distribution**:
  - 12V/10A switching PSU (mains input 220–240V AC)
  - 12V→5V buck converter (3A, with LC filtering)
  - 5V Li-ion UPS module (emergency runtime backup)
  - 12A main fuse, 3A fused subsystem outputs
- **Storage**: 64GB Class 10 microSD card (Pi OS + SQLite database)
- **Mechanical**: 10-slot turntable carousel, GT2 timing belt + pulleys, acrylic or 3D-printed prototype enclosure

## Operation

### Student Card Collection Workflow

**Stage 1: OTP Verification**

1. Student enters registration number on touchscreen
2. Pi queries university database via HTTPS (or uses cached student record)
3. Pi generates 6-digit OTP, hashes with bcrypt, stores in database
4. BRIQ SMS API sends OTP via SMS (+ email if configured)
5. Student enters OTP; Pi validates hash match within 24h window

**Stage 2: PIN Setup / Verification**

- **Returning student**: Enters existing PIN; Pi validates against bcrypt hash
- **First-year student**: Receives temporary PIN in SMS, enters it, then creates permanent PIN (stored as is_temp_pin=FALSE)

**Stage 3: Card Dispensing**

1. Pi sends SPI frame: `[0x10, slot_index, checksum]` (ROTATE_TO_SLOT)
2. STM32 rotates carousel stepper until target slot aligns with front gate
3. Pi sends SPI frame: `[0x11, 0x00, 0x11]` (EJECT_CARD)
4. STM32 activates servo; card pushed to student collection point
5. Pi logs successful collection to audit_log; clears session; returns to IDLE

**Stage 4: Timeout & Cleanup**

- Inactivity > 60 seconds → Pi auto-clears session, returns to IDLE
- SessionManager.teardown() erases volatile state (prevents card hijacking)

### Lockout Policy

| Failure Type | Attempts | Cooldown   | Effect                      |
| ------------ | -------- | ---------- | --------------------------- |
| OTP Failure  | 3        | 30 minutes | Soft lockout; retry allowed |
| PIN Failure  | 3        | 24 hours   | Hard lockout; admin review  |

### OCR Pipeline (Batch Loading)

**Three-stage image processing** (target <3 sec per card):

1. **Capture**: IR sensor on Conveyor 1 triggers CSI camera frame
2. **Preprocessing**: Grayscale → adaptive threshold → deskew → ROI crop (OpenCV)
3. **Extraction**: Tesseract 5 (`--psm 7` single-line mode) with alphanumeric whitelist
4. **Validation**: Regex match against university registration format
5. **Gating**: Low confidence (<70%) or regex mismatch → divert to reject bin

## Installation & Setup

### Raspberry Pi 5 Prerequisite Setup

1. **OS Installation**

   Flash Raspberry Pi OS Lite (bookworm, 64-bit ARM) to microSD via Raspberry Pi Imager.

2. **Enable Interfaces** (via `sudo raspi-config`)

   ```
   Interface Options → SPI (enable)
   Interface Options → Camera (enable)
   Interface Options → SSH (enable)
   ```

3. **System Packages**

   ```bash
   sudo apt update && sudo apt install -y \
     python3.11 python3.11-venv python3.11-dev \
     libopencv-dev tesseract-ocr libtesseract-dev \
     libsm6 libxrender-dev libxext-dev \
     libatlas-base-dev libjasper-dev libtiff5 libharfbuzz0b libwebp6 \
     python3-spidev avahi-daemon
   ```

### Kiosk Application Setup

```bash
cd /home/pi/card-issuance-system/kiosk_brain

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Initialize SQLite database
cd db
python3 init_db.py         # Creates kiosk.db with schema
cd ..
```

### Configuration

Edit `config.py` with production values:

- `BRIQ_API_KEY`: BRIQ Solutions API key (from account dashboard)
- `BRIQ_SENDER_ID`: SMS sender name (max 11 chars)
- `BRIQ_BASE_URL`: BRIQ endpoint (usually `https://karibu.briq.tz`)
- `API_BASE_URL`: University database endpoint (e.g., `http://university-db.local:5000`)
- `API_TIMEOUT_SEC`: Network timeout (default 5 sec)
- `OTP_EXPIRY_HOURS`: OTP validity window (default 24 hours)
- `PIN_LOCKOUT_HOURS`: Hard lockout duration (default 24 hours)

**NEVER commit credentials to git**; use environment variables or secure config management in production.

### Autostart Service (systemd)

Create `/etc/systemd/system/kiosk.service`:

```ini
[Unit]
Description=Smart ID Card Distribution Kiosk
After=network-online.target avahi-daemon.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/card-issuance-system/kiosk_brain
ExecStart=/home/pi/card-issuance-system/kiosk_brain/venv/bin/python main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable autostart:

```bash
sudo systemctl enable kiosk.service
sudo systemctl start kiosk.service
sudo systemctl status kiosk.service
```

### STM32 Firmware Development

- **IDE**: STM32CubeIDE (Linux-native)
- **Project**: Located in `firmware/real_time_controller/`
- **Configuration**:
  - SPI1 in slave mode (PA4=CS, PA5=CLK, PA6=MISO, PA7=MOSI)
  - TIM2, TIM3 for stepper PWM (1–10 kHz configurable frequency)
  - GPIO outputs for stepper DIR pins, solenoid control
  - GPIO inputs (PULL_UP) for IR and Hall-effect sensors
- **Build & Flash**: Use ST-Link v2 programmer; build via CubeIDE or Makefile
- **SPI Protocol**: See `kiosk_brain/SPI_PROTOCOL.md` for frame format and command table

### Unit & Integration Tests

```bash
cd kiosk_brain/tests

# Unit tests
python3 -m unittest tests.test_auth -v          # Authentication logic (bcrypt, OTP)
python3 -m unittest tests.test_ocr -v           # OCR pipeline (OpenCV preprocessing)
python3 -m unittest tests.test_spi -v           # SPI frame encoding/checksums

# Integration test (requires mock API running)
python3 -m unittest tests.test_integration -v
```

### Mock University API (Development Only)

The mock API simulates the real university student database for testing. See `mock_db_api/README.md` for setup.

```bash
cd mock_db_api
pip install -r requirements.txt
python app.py
# Runs on https://localhost:5000, advertised as university-db.local (via mDNS)
```

## Performance Targets

| Metric              | Target           | Notes                                                        |
| ------------------- | ---------------- | ------------------------------------------------------------ |
| **Card throughput** | 10–15 cards/min  | Batch mode: conveyor feed + carousel index + servo eject     |
| **OCR accuracy**    | 98%+             | Assumes uniform lighting and clean card surface              |
| **Pi startup**      | <30 sec          | OS boot + Kivy initialization + database open                |
| **SPI latency**     | <10 ms           | Motor response imperceptible to user (<100 ms total)         |
| **Auth response**   | <2s local        | SQLite hash validation only                                  |
| **API round-trip**  | <5s (with retry) | Network + university DB query (includes exponential backoff) |
| **SMS delivery**    | <60 sec          | BRIQ Solutions typical delivery window (Tanzania)            |
| **Session timeout** | 60 sec           | Inactivity threshold before automatic teardown               |

## Limitations & Future Work

### Current Release (Phase 4)

- **SPI**: Unencrypted communication (trusted local link only; not a concern in kiosk setting)
- **OCR**: Assumes uniform diffuse lighting (field lighting critical for ~98% accuracy)
- **Carousel**: 10-slot prototype (firmware-configurable to 20-slot with mechanical change)
- **Authentication**: SMS-only OTP delivery (email future enhancement)
- **Database**: SQLite (single-instance; no concurrent access needed)

### Hardware Status (Phase 5: In Progress)

- Mechanical prototype not yet assembled (waiting for motor/chassis components)
- Firmware skeleton defined; SPI protocol complete (implementation pending)
- Power distribution topology designed (not yet wired)
- 3D-printed carousel CAD model in progress

### Known Issues

- Pi Camera Module v2 uses legacy CSI connector (Pi 5 requires adapter cable)
- Tesseract 5 may require language data pack installation for non-English text
- mDNS discovery (avahi) unreliable over some corporate WiFi networks (fallback to IP config required)

### Planned Enhancements

- **Q4 2026**: SPI frame encryption (optional, low priority), multilingual OCR, backup SMS provider (Twilio), wireless firmware updates via U-Boot
- **Future**: Biometric fingerprint verification, on-site card printing, encrypted tamper detection seals

## Additional Resources

- **Architecture Diagrams**: See `docs/kiosk_architecture.html` (Kiosk flow state machines, hardware interconnect)
- **Build Instructions**: See `BUILD.md` (phase-by-phase task breakdown and current progress)
- **Hardware Design**: See `hardware/README.md` (power distribution, motor control implementation)
- **Firmware Design**: See `firmware/BUILD.md` (STM32 configuration, pin assignments)
- **SPI Protocol**: See `kiosk_brain/SPI_PROTOCOL.md` (3-byte frame format, command/response codes)
- **Kiosk-Brain Subsystem**: See `kiosk_brain/README.md` (module architecture, screen flow)
- **Mock API**: See `mock_db_api/README.md` (development database simulation)
- **Database Schema**: See `kiosk_brain/db/DATABASE_DESIGN.md` and `schema.sql`

## References

### Software Libraries & Frameworks

- **Kivy 2.3.1**: Touch UI framework · <https://kivy.org/doc/>
- **OpenCV 4.13.0**: Computer vision preprocessing · <https://docs.opencv.org/>
- **Tesseract 5**: OCR engine · <https://github.com/UB-Mannheim/tesseract/wiki>
- **Python bcrypt**: Password & OTP hashing · <https://github.com/pyca/bcrypt>
- **requests 2.33.0**: HTTP client (API calls) · <https://requests.readthedocs.io/>
- **SQLite 3**: Embedded database · <https://www.sqlite.org/lang.html>
- **Flask 2.x**: Mock API framework · <https://flask.palletsprojects.com/>

### Hardware & Microcontrollers

- **STM32F401RE Reference Manual**: <https://www.st.com/resource/en/reference_manual/dm00031020-stm32f4-series-reference-manual.pdf>
- **A4988 Stepper Driver**: <https://www.pololu.com/product/1182>
- **NEMA 17 Stepper Motor**: ~1.5A RMS, ~48mm frame
- **SG90 Servo Motor**: 3–6V logic, torque ~2.5 kg⋅cm
- **Raspberry Pi 5 Documentation**: <https://www.raspberrypi.com/documentation/computers/raspberry-pi.html>

### SMS Gateway & APIs

- **BRIQ Solutions (Tanzania)**: <https://docs.briq.tz/api-reference/>
- **mDNS / Avahi**: <https://avahi.org/>
- **SPI Protocol**: <https://www.kernel.org/doc/html/latest/spi/index.html>

### Development Tools

- **STM32CubeIDE**: <https://www.st.com/en/development-tools/stm32cubeide.html>
- **Git**: Version control · <https://git-scm.com/>
- **Pytest**: Python unit testing framework · <https://docs.pytest.org/>
