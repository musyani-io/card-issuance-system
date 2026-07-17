# Hardware Implementation

**Status**: Phase 5 (Mechanical Prototype) — Active prototyping. Target platform is the Arduino Mega 2560 with the 2-byte ASCII SPI protocol.

This section outlines the hardware architecture, pin mappings, and integration strategy for motor control, power distribution, sensing, and inter-controller communication.

---

## Power Distribution Architecture

**Topology**: Single 220VAC-to-12VDC primary power supply with step-down logic regulation and star common ground.

- **Primary Source**: 220VAC-to-12VDC switching power supply.
- **Logic Power**: An LM2596 buck converter steps down the 12V rail to 5VDC to power the Raspberry Pi 5, the Arduino Mega 2560, and logic sensors.
- **Common Reference**: All grounds (12V power supply negative terminal, LM2596 input/output grounds, Raspberry Pi ground, and Arduino Mega ground) are tied together at a single common reference point (star ground configuration) to eliminate ground loop noise.

| Rail | Voltage | Components | Regulation / Source | Grounding |
| --- | --- | --- | --- | --- |
| **Primary** | 12V | Stepper drivers, solenoid lock, servos | 220VAC to 12VDC PSU | Single-Point Common Ground |
| **Logic** | 5V | Raspberry Pi 5, display, Arduino Mega, sensors | LM2596 Buck Converter | Single-Point Common Ground |

**Implementation Tasks**:
1. Mount the 220VAC-to-12VDC primary switching power supply securely.
2. Connect the LM2596 buck converter to the 12V rail and calibrate its output to exactly 5.0V before connecting any logic components.
3. Establish a single ground terminal block where all grounds are physically joined at one point.
4. Add safety fuses where appropriate (e.g. on the primary 12V rail).
5. Use adequate gauge wire (e.g. AWG 16–18 for power paths, AWG 22 for logic grounds) to prevent voltage drops.

---

## Motor Driver & Stepper Motor Control

**Architecture**: 28BYJ-48 geared stepper motor (5V/12V) with ULN2003 Darlington driver board.

**Driver Connection**:
- **Inputs**: IN1, IN2, IN3, IN4 connected to Arduino Mega digital output pins.
- **Power**: 5V/12V (depending on motor variant) + GND.
- **Outputs**: 4-phase coil connector to the 28BYJ-48 stepper motor.

**Arduino Mega Pin Mapping**:
- `IN1` ──→ Digital Pin 30
- `IN2` ──→ Digital Pin 31
- `IN3` ──→ Digital Pin 32
- `IN4` ──→ Digital Pin 33

> [!NOTE]
> The Arduino code constructs the stepper interface using `Stepper stepper(2048, 30, 32, 31, 33)` (IN1, IN3, IN2, IN4 pin order) to match the correct phase sequence required by the 28BYJ-48.

**Tuning Parameters**:
- **Steps per full rotation**: 2048 steps (geared down).
- **Speed**: 5 RPM (configured in firmware to maximize torque and prevent mechanical slippage).
- **Homing and Carousel Compartments**:
  - Carousel has 3 compartments: A, B, and C (Failure/Reject slot).
  - Homing aligns to Compartment A (0° / 0 steps).
  - Compartment B (120°) is located at 683 steps.
  - Compartment C (240°) is located at 1365 steps.

---

## Servo Motor Control (SG90 Servo)

**Servo**: Single SG90 analog micro-servo for the card holder / front gate release mechanism.

**Control Signal**: PWM at 50 Hz, 544–2400µs pulse width.
- **Origin position**: 544µs (0° hold position).
- **Active release position**: Mapped to 70° in the firmware to retract the card gate.

**Arduino Mega Connection**:
- **Vcc**: 5V Logic Rail (from LM2596 output)
- **GND**: Common Ground
- **Signal**: Digital Pin 22 (PWM)

**Firmware Logic**:
To prevent sudden jumps on startup, the pulse width is preloaded to the origin pulse (544µs) before attaching the servo object. The servo moves smoothly using a microsecond-stepping sweep routine.

---

## Raspberry Pi 5 ↔ Arduino Mega 2560 SPI Communication

**Bus Specification**: SPI Mode 0, 100 kHz clock speed. 

**Physical Interconnect**:
- **Raspberry Pi 5 (Master)**:
  - GPIO 11 (SCLK) ──→ Mega Pin 52 (SCK)
  - GPIO 10 (MOSI) ──→ Mega Pin 51 (MOSI)
  - GPIO 9  (MISO) ───→ Mega Pin 50 (MISO)
  - GPIO 8  (CE0)  ───→ Mega Pin 53 (SS, active low)
  - Common Ground  ───→ GND (tied to the single-point common ground)

> [!IMPORTANT]
> The Arduino Mega operates at 5V logic, while the Raspberry Pi 5 operates at 3.3V. You **MUST** use an appropriate 5V-to-3.3V logic level shifter on the MISO line (Mega TX to Pi RX) to protect the Raspberry Pi GPIO pins.

**2-Byte ASCII Protocol**:
Every transmission frame consists of exactly **2 ASCII characters** without checksum bytes, terminated by a null character in the receiver buffer.

### Status and Routing Frames (Pi → Mega)

| ASCII Frame | Transaction Type | Action / Target Meaning |
| ----------- | ---------------- | ----------------------- |
| `"10"`      | Ingestion (OCR)  | Route Compartment A to Entrance (0°) and release card |
| `"11"`      | Ingestion (OCR)  | Route Compartment B to Entrance (120°) and release card |
| `"12"`      | Ingestion (OCR)  | Route Compartment C to Entrance (240°) and release card |
| `"00"`      | Ingestion (OCR)  | OCR Error/Failure: Route Compartment C to Entrance (240°) |
| `"20"`      | Collection (UI)  | Route Compartment A to Exit (180°) and await pickup |
| `"21"`      | Collection (UI)  | Route Compartment B to Exit (300°) and await pickup |
| `"FF"`      | Collection (UI)  | UI Transaction Failure / Cancelled |

---

## Integration Checkpoint

Before moving to full system integration, validate in sequence:
1. **Power Rails**: Verify stable 12V and 5V outputs under load; check for noise/ripple.
2. **Stepper driver**: Test rotation in both directions; verify that speed is set to 5 RPM to ensure torque.
3. **Servo Gate**: Confirm card holder gate opens to 70° and returns to origin (0°).
4. **SPI Loopback**: Send characters `"10"`, `"11"`, `"20"`, etc., from `spi_master.py` and confirm serial outputs on the Arduino Mega.
