# Card Issuance System Summary

## Purpose

This repository contains the full Smart ID Card Distribution Kiosk project: a distributed embedded system for autonomous university ID card issuance, collection, authentication, and audit logging.

The system is split into four major layers:

- Raspberry Pi 5 application layer for UI, OCR, SQLite, API access, SMS delivery, and SPI master control
- STM32 Nucleo-F401RE control layer for motors, servos, sensors, and SPI slave handling
- Hardware design layer for power distribution, mechanics, PCB work, and enclosure planning
- Documentation layer for architecture, phase tracking, workflow, and formal project reports

## Repository Structure

### Root level

- `README.md` - system overview, high-level architecture, operational flow, and repository map
- `BUILD.md` - phase plan and progress tracker across the full project lifecycle
- `.gitignore` - repository ignore rules

### `docs/`

This folder stores project and business documentation, formal proposals, visual diagrams, and architecture references.

- `kiosk_architecture.html` - interactive architecture and state-machine documentation
- `carousel_3d_v2.html` - 3D carousel visualization
- `official/` - concept note, reports, and block diagram material
- `business/` - business plan and supporting proposal documents
- `primary/` - main proposal source material

### `kiosk_brain/`

This is the Raspberry Pi 5 Python application layer. It is the operational brain of the kiosk.

- `main.py` - Kivy application entry point and screen routing
- `config.py` and `config.example.py` - runtime configuration and secrets template
- `requirements.txt` - Pi-side Python dependency set
- `SPI_PROTOCOL.md` - byte-level SPI contract between the Pi and STM32
- `db/` - SQLite schema, initialization script, and database design notes
- `modules/` - core business logic packages
- `ui/` - Kivy screen classes, widgets, constants, and styling
- `tests/` - OCR, auth, ingest, SPI, and generated sample-output scripts

### `mock_db_api/`

This folder contains the development-only mock university database API.

- `app.py` - Flask REST server for student lookup
- `config.py` - API and MySQL configuration
- `requirements.txt` - Flask and MySQL dependencies
- `README.md` - setup and endpoint usage notes

### `firmware/`

This folder contains the STM32 embedded controller project and build notes.

- `BUILD.md` - firmware bring-up, pin map, SPI, and phase 5 integration plan
- `pin_assignment.txt` - GPIO and peripheral pin map
- `real_time_controller/` - STM32CubeIDE project with source, startup, linker scripts, and generated build artifacts

### `hardware/`

This folder contains the physical system design assets.

- `README.md` - power, actuator, sensor, SPI, and integration architecture
- `BUILD.md` - hardware assembly and implementation guidance
- `kiCAD/` - KiCAD PCB design files
- `Altium/` - Altium design references and schematics
- `FreeCAD/` - mechanical CAD design and exports
- `simulations/` - Proteus simulation projects and outputs
- `datasheets/` - component reference PDFs

## Core System Architecture

The kiosk is designed as a distributed embedded workflow:

1. Staff loads a batch of cards into the kiosk.
2. The Pi captures card images, detects the card, corrects perspective, and runs OCR.
3. The Pi validates the registration number and looks up student records.
4. Student credentials are stored in SQLite and sent by SMS and email.
5. During collection, the student authenticates with OTP and PIN.
6. The Pi sends SPI commands to the STM32 to rotate the carousel, open latches, or eject a card.
7. All important actions are written to the audit log.

The architecture is intentionally split so that user interface and data handling stay on the Pi, while deterministic hardware control stays on the STM32.

## End-to-End Workflow

### 1. Staff batch loading workflow

This is the OCR and ingestion path used when new cards are loaded into the kiosk.

1. Staff opens the kiosk batch-loading workflow from the touchscreen.
2. The system verifies staff access and pre-scan conditions.
3. A card reaches the scan station.
4. The Pi camera captures the image.
5. The OCR pipeline performs card detection, perspective correction, grayscale conversion, thresholding, ROI extraction, and text recognition.
6. The registration number is validated against the expected pattern.
7. The Pi queries the university database through the mock API.
8. The student record is written to SQLite.
9. OTP and temporary PIN logic is applied depending on student type.
10. SMS and email credentials are sent.
11. The card is assigned a slot and the batch progress UI is updated.

### 2. Student collection workflow

This is the path used when a student arrives to collect an issued card.

1. The kiosk starts in idle mode.
2. The student selects the returning-student or first-year path.
3. The student enters their registration number, OTP, and PIN as required.
4. The Pi verifies credentials through the auth module.
5. If the student is first-year and has a temporary PIN, the system forces a permanent PIN setup step.
6. On success, the Pi sends SPI commands to the STM32 to rotate the carousel and eject the card.
7. The kiosk shows a success screen and then returns to idle.

### 3. Error and lockout workflow

The project includes explicit handling for invalid credentials, session timeout, and lockouts.

1. OTP and PIN failures are counted in SQLite.
2. Repeated failures trigger soft or hard lockout depending on the factor.
3. The locked state is shown on the UI with a countdown.
4. Audit logs capture failures, lockouts, and completed collections.
5. Session cleanup is mandatory before returning to idle.

## Pi Application Layer Details

### `main.py`

`main.py` is the Kivy entry point.

- It creates a single `KioskApp` instance.
- It builds the `ScreenManager` and all UI screens.
- It binds screen transitions to session updates and auth actions.
- It schedules a timeout check every second.
- It tears down the session before returning to idle.

The screen flow includes:

- idle and welcome states
- registration entry
- OTP entry
- PIN entry
- first-year PIN setup
- confirmation and success states
- error and lockout states
- staff login, checklist, progress, and summary screens

### `modules/`

This folder contains the business logic.

- `auth.py` - OTP and PIN generation, bcrypt hashing, lockout enforcement, temporary PIN handling, and audit logging
- `database.py` - SQLite access, student lookup, slot assignment, ingestion helpers, and transaction support
- `api_client.py` - HTTP client for the university database service with retries and timeout handling
- `ocr.py` - image preprocessing, OCR execution, and registration-number extraction
- `sms_client.py` - credential delivery through the SMS gateway and retry handling
- `spi_master.py` - SPI frame building, command dispatch, response parsing, and hardware control wrappers
- `session_manager.py` - in-memory session state, timeout tracking, and teardown logic
- `card_detector.py` - card-finding logic used by the OCR pipeline
- `__init__.py` - package marker

### `ui/`

This folder defines the Kivy frontend.

- `screens.py` - screen classes for student and staff flows
- `styled_widgets.py` - reusable UI widgets
- `styles.kv` - Kivy language layout and styling definitions
- `constants.py` - screen names, colors, and UI constants

### `db/`

The database layer uses SQLite as the local system of record.

The schema contains five core tables:

- `students` - student master data
- `cards` - card slot and lifecycle tracking
- `authentication` - OTP, PIN, lockout, and temporary PIN state
- `audit_log` - append-only event trail
- `batches` - staff loading session metadata

The design emphasizes:

- hashed credentials, never plaintext
- immutable audit logging
- a natural key based on registration number
- cleanup through application logic rather than destructive cascade behavior

### `tests/`

The tests folder is built around small scripts and generated outputs.

- OCR sample generators create image and thresholding outputs for manual inspection
- auth tests cover OTP, PIN, and lockout logic
- ingest tests cover database flow and card loading
- SPI tests validate frame format and loopback behavior
- output folders hold generated intermediate images and OCR artifacts

## Mock University API Details

The mock database API exists so the Pi can be tested without the real university service.

It provides a single student lookup endpoint:

- `GET /students/<reg_number>`

It uses:

- Flask for the web server
- MySQL for the backing student database
- an API key header for access control
- a development-friendly local configuration model

The intended flow is:

1. The Pi asks for a student record by registration number.
2. The API queries the MySQL `students` table.
3. The API returns JSON on success or a clear error code on failure.
4. The Pi continues the issuance workflow with the returned student data.

## Firmware Details

The STM32 project under `firmware/real_time_controller/` is the hardware executor.

It contains:

- CubeMX and STM32CubeIDE project configuration
- startup code and linker scripts
- interrupt handlers
- HAL-based initialization code
- source files for SPI, GPIO, timers, and system setup

The firmware work is centered on:

- SPI slave communication with the Pi
- stepper pulse generation for the carousel and conveyor
- servo PWM for eject and latch actions
- sensor polling for home and safety signals
- door lock control for the solenoid

## Hardware Design Details

The `hardware/` folder records the physical implementation strategy.

### Power

The power plan separates the system into logic, primary motor power, and backup rails.

- 12V rail for motors, solenoid, and driver electronics
- 5V rail for Pi, STM32, display, and sensors
- backup 5V runtime path for graceful shutdown and limited operation

### Motion and actuation

- NEMA 17 steppers drive the carousel and conveyor
- SG90 servos handle eject and latch actions
- a MOSFET controls the solenoid lock
- a hall sensor provides carousel homing
- IR break-beam sensors detect presence and safety states

### Mechanical assets

- FreeCAD stores the prototype geometry and exported STL files
- KiCAD and Altium store board-level electrical designs
- Proteus simulations validate power-protection ideas before hardware build-out

## Build and Development Workflow

The docs describe a staged implementation strategy:

1. OCR and image preprocessing first.
2. Database and mock API second.
3. Authentication and credential delivery third.
4. Kivy UI and SPI integration fourth.
5. STM32 firmware and mechanical assembly fifth.
6. Enclosure, system tests, and final documentation last.

That order matters because it validates the hardest-to-debug software pieces before the mechanical system adds complexity.

## Implementation Status Snapshot

The repository contains multiple progress snapshots in the docs. The most useful summary is:

- Phase 1 OCR work is heavily documented and partially complete in the roadmap, with generated outputs and preprocessing scripts present.
- Phase 2 database and mock API work is largely complete, including schema, API client, and local data flow.
- Phase 3 authentication is complete according to the phase tracker, including OTP, PIN, temp PIN, lockout, and audit logging.
- Phase 4 UI and SPI integration is mostly complete, with screen architecture, protocol design, and Pi-side SPI driver in place.
- Phase 5 firmware and mechanical integration is underway, with pin mapping, SPI loopback, and control-path planning documented.
- Hardware design assets exist for power, protection, PCB, and mechanical work, but the complete physical integration is still a build-phase activity.

## Results So Far

The project already has the key software and documentation foundations needed for the kiosk workflow:

- a working Pi-side application architecture
- a defined SQLite schema and audit model
- a mock API for testing external student lookup
- a defined SPI protocol between Pi and STM32
- a firmware bring-up plan with confirmed pin assignments
- hardware design files for power, protection, and mechanical subassemblies

The repository also shows that the team has already validated important milestones such as:

- credential hashing and verification logic
- temporary PIN handling for first-year students
- lockout and audit logging behavior
- SPI framing and loopback communication
- UI routing and timeout enforcement

## Ongoing Optimization

The documentation points to a few active optimization areas:

1. Improve OCR robustness by tuning preprocessing, ROI selection, and anchor detection.
2. Keep the session manager teardown path strict so no ghost session data survives a screen transition.
3. Finish the card ingestion pipeline so OCR, lookup, database write, and slot assignment are fully atomic.
4. Complete the remaining STM32 actuator and sensor routines so the Pi can drive the real hardware reliably.
5. Validate the physical build under load, especially power noise, homing repeatability, and sensor timing.
6. Keep the mock API and Pi configuration aligned so test and deployment environments stay interchangeable.

## Practical Notes

- The project is intentionally headless-friendly for Pi-side development.
- OCR and image scripts expect generated outputs to land under `kiosk_brain/tests/outputs/` and related fixture folders.
- The docs note that the workspace should use the project virtual environment for image and OCR work because the system Python may not have the required packages.
- Configuration templates are kept separate from active secrets so the kiosk can be deployed without committing credentials.

## Bottom Line

This repository is not a single app. It is a complete kiosk system made of software, firmware, hardware design, and operational documentation. The workflow is already well defined end to end: detect and ingest cards, authenticate students, dispense cards through STM32-controlled mechanics, and record every important event in the local database.
