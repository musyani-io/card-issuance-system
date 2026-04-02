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

- Python 3.11 runtime with Kivy 2.3 GPU-accelerated UI
- 7" DSI touchscreen interface (800×480 resolution)
- OCR pipeline (OpenCV + Tesseract 5)
- SQLite database (student records, auth credentials, audit logs)
- SPI master communication with STM32
- HTTPS API client for university database and SMS gateway

**STM32 Nucleo-F401RE (Hardware Control)**

- SPI slave mode receiving commands from Pi
- Motor control (NEMA 17 stepper × 2 for carousel and conveyor)
- Servo control (SG90 × 2 for ejector and expired card latch)
- Solenoid lock control (fail-secure design)
- Sensor polling (4× IR break-beam, 1× Hall-effect for homing)
- Hardware interlock: door-open sensor → automatic motor disable (failsafe)

### Mechanical Subsystems

- **Turntable Carousel**: 10-slot disc with neodymium card retention; expandable to 20-slot
- **Conveyor Systems**: Input transport (staff tray → carousel rear gate) + Output (carousel front → student collection point)
- **Camera Stations**: CSI camera above Conveyor 1 for batch OCR; USB camera in front-panel expired card slot
- **Dispensing**: SG90 servo flap at turntable front gate for individual card ejection
- **Security**: 12V solenoid lock on staff access door (energized-to-lock, fail-secure)

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
├── README.md                    # This file
├── BUILD.md                     # Build and deployment guide
├── docs/                        # Architecture diagrams and specifications
├── kiosk-brain/                 # Raspberry Pi Python application
│   ├── main.py                  # Kivy app entry point
│   ├── config.py                # Environment configuration (credentials, timeouts)
│   ├── requirements.txt         # Python dependencies
│   ├── modules/                 # Core business logic
│   ├── ui/                      # Kivy screens and UI components
│   ├── tests/                   # Unit and integration tests
│   ├── db/                      # SQLite schema and initialization
│   └── data/logs/              # Application audit logs
├── mock-db-api/                 # Flask mock university API (development)
└── firmware/                    # STM32 firmware (separate repo/project)
```

## Architecture Details

### Network Communication

**Pi ↔ University Database**: HTTPS+mDNS (resolves `university-db.local` automatically, no hardcoded IPs)

- Endpoint: `GET /students/{reg_number}`
- Timeout: 5 seconds with 3× exponential backoff retry
- Supports WiFi and mobile hotspot failover

**Pi ↔ SMS Gateway**: HTTPS to BRIQ Solutions API

- Endpoint: POST `/v1/message/send-instant`
- Credentials: API key, sender ID in `config.py`
- Retry queue: Failed sends stored in SQLite, background retry every 15 min

**Pi ↔ STM32**: SPI protocol (local communication only)

- Frame format: [COMMAND][PARAMETER][CHECKSUM]
- Commands: Carousel rotation, card ejection, lock/unlock, sensor polling, homing
- Safety: Pi crash → STM32 receives no commands → all motors remain stopped

### Authentication & Sessions

**Two-Factor Authentication**

- **Factor 1 (OTP)**: 6-digit code sent via SMS + email, bcrypt-hashed in DB, 24h expiry
- **Factor 2 (PIN)**: 4–6 digits; returning students use existing PIN, first-years create permanent PIN after temp PIN validation
- **Lockout**: 3 consecutive failures → 30-min cooldown (OTP) or 24-h hard lockout (PIN)

**Session Management**

- Per-transaction state tracked in volatile SessionManager object
- Explicit cleanup on transaction completion or 5-min timeout
- All events (success/failure) logged to immutable audit_log table

### Database

**SQLite schema** includes:

- `students`: Registration number (PK), name, email, phone, programme, status
- `authentication`: OTP hash, PIN hash, is_temp_pin flag, failed attempt counters, lockout expiry
- `cards`: Card ID, batch reference, slot index, status, timestamps
- `audit_log`: Immutable event log (session_start, otp_sent, auth_failed, collection_success, etc.)
- `batches`: Batch metadata, card counts, timestamps

**Automatic cleanup**: Background cron purges old records every 120 days (carousel slot exhaustion prevention)

### Power Architecture

- **Primary Rail (12V, 10A)**: Motors, drivers, solenoid lock
- **Logic Rail (5V, regulated)**: Raspberry Pi, display, STM32, servos
- **Separation**: Motors on 12V rail, logic on 5V buck-converter (prevents stepper noise on Pi microSD)
- **UPS (5V Li-ion)**: Backup power for 5–10 min runtime (Pi+display+STM32 only, not motors)
  - Ensures SQLite database closure on mains failure
  - Motors stop cleanly (no backup) — mechanically safe

### Sensors

| Sensor     | Type        | Purpose                                   |
| ---------- | ----------- | ----------------------------------------- |
| IR1        | Break-beam  | Staff door open detection                 |
| IR2        | Break-beam  | Rear gate card detection (carousel)       |
| IR3        | Break-beam  | Front gate card ejection confirmation     |
| IR4        | Break-beam  | Expired card slot insertion               |
| Hall A3144 | Hall-effect | Carousel absolute home reference (slot 0) |

### Bill of Materials (Key Components)

- Raspberry Pi 5 (4GB), STM32 Nucleo-F401RE
- Official 7" DSI touchscreen, Pi Camera Module v2 (CSI), USB webcam (720p)
- NEMA 17 stepper motors (×2), SG90 servos (×2), 12V solenoid lock
- A4988 stepper drivers (×2), IRLZ44N MOSFET, IR sensors (×4), Hall-effect sensor
- 10-slot turntable carousel, GT2 timing belt and pulleys
- 12V/10A switching PSU, 12V→5V buck converter, 5V UPS Li-ion module
- 64GB Class 10 microSD card

## Operation

### Student Card Collection Flow

1. **OTP Phase**: Student enters registration number → Pi queries API → generates OTP → sends via SMS+Email
2. **OTP Verification**: Student enters 6-digit OTP on touchscreen → Pi validates against bcrypt hash
3. **PIN Phase**:
   - Returning student enters existing PIN
   - First-year student receives temporary PIN in SMS, enters it, then creates permanent PIN
4. **Collection**: Pi signals STM32 to rotate carousel to slot and eject card → student collects
5. **Logging**: All events recorded in audit_log (timestamps, success/failure, session ID)

### Authentication Lockout Policy

- **OTP Failures**: 3 consecutive failures → 30-minute cooldown (soft lockout, retry allowed after cooldown)
- **PIN Failures**: 3 consecutive failures → 24-hour hard lockout (flagged for administrator review)

### OCR Pipeline

**Three-Stage Processing**:

1. **Image Capture**: CSI or USB camera (triggered by IR sensor)
2. **Preprocessing**: Grayscale → adaptive thresholding → deskew → ROI crop (OpenCV)
3. **Text Extraction**: Tesseract 5 with alphanumeric whitelist → regex validation against university format

**Confidence Gating**: Low-confidence cards routed to reject bin (never carousel)
**Performance**: <3 seconds per card scan

## Installation & Setup

### Raspberry Pi Environment

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

- Develop in STM32CubeIDE (Linux-native IDE)
- Configure SPI1 in slave mode, GPIO interrupts, motor timers
- Compile and flash via ST-Link programmer
- See `firmware/` directory for project structure

### Unit Tests

```bash
cd kiosk-brain/tests
python -m unittest tests.test_auth -v          # Authentication tests
python -m unittest tests.test_ocr -v           # OCR pipeline tests
python -m unittest tests.test_spi -v           # SPI protocol tests
```

## Performance Targets

| Metric              | Target                       | Notes                                 |
| ------------------- | ---------------------------- | ------------------------------------- |
| Card throughput     | 10–15 cards/min (batch mode) | Conveyor + carousel + servo actuation |
| OCR accuracy        | 98%+                         | Assumes well-lit cards                |
| Pi startup          | <30 sec                      | OS boot + Kivy init                   |
| SPI command latency | <10 ms                       | Motor imperceptible to user           |
| Auth response       | <2s (local) / <5s (network)  | SQLite vs API round-trip              |
| SMS delivery        | <60 sec                      | BRIQ Solutions typical window         |

## Limitations & Future Work

### Current Release

- SPI communication: Unencrypted (trusted local network only)
- OCR: Assumes uniform lighting (field lighting critical for production)
- Carousel: 10-slot prototype (expandable to 20 via firmware)
- Python 3.11 on ARM64 with Kivy 2.3.1

### Planned Enhancements

- **Q4 2026**: SPI frame encryption, multilingual OCR, backup SMS provider, wireless firmware updates
- **TBD**: Biometric fingerprint scanner, on-site card printing, encrypted tamper detection

## Additional Resources

- **Architecture Diagrams**: See `docs/kiosk_architecture.html`
- **Build Instructions**: See `BUILD.md`
- **API Client Documentation**: `mock-db-api/README.md`
- **Kiosk-Brain Subsystem**: `kiosk-brain/README.md`

## References

- **OpenCV Documentation**: <https://docs.opencv.org/>
- **Tesseract OCR**: <https://github.com/UB-Mannheim/tesseract/wiki>
- **Kivy Framework**: <https://kivy.org/doc/>
- **BRIQ Solutions**: <https://docs.briq.tz/api-reference/hello-briq>
- **SQLite**: <https://www.sqlite.org/lang.html>
- **STM32 HAL Reference**: <https://www.st.com/resource/en/reference_manual/dm00031020-stm32f446xx-advanced-arm-based-32-bit-mcus-stm32f4-series-reference-manual-stmicroelectronics.pdf>
