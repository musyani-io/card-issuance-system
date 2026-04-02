# Hardware Implementation

**Status**: Phase 5 (Mechanical Prototype) — In planning phase. Detailed schematics and implementation guides to follow as components arrive and testing begins.

This section outlines the hardware architecture and integration strategy for motor control, power distribution, sensing, and inter-controller communication.

## Power Distribution Architecture

**Topology**: Three isolated rails with manual and automatic switching

| Rail        | Voltage         | Current | Components                                          | Protection                        |
| ----------- | --------------- | ------- | --------------------------------------------------- | --------------------------------- |
| **Primary** | 12V             | 10A     | NEMA motors, stepper drivers, solenoid lock, servos | 12A fuse, relay switching         |
| **Logic**   | 5V (regulated)  | 3A      | Raspberry Pi, display, STM32 logic, sensors         | 3A buck converter, TVS diode      |
| **Backup**  | 5V (Li-ion UPS) | 1A      | Pi + display + STM32 runtime on mains loss          | Ideal diode, automatic switchover |

**Implementation Tasks** (from BUILD.md Phase 5):

1. Install 12V/10A switching PSU (mains input 220–240V)
2. Wire 12V→5V buck converter with input filtering (1000µF, 100nF capacitors)
3. Connect UPS module with ideal diode to create seamless switchover on power loss
4. Add 12A main fuse on 12V rail, 3A fused outputs to each subsystem
5. Use thick gauge wire (AWG 16–18) for all power distribution to minimize voltage drop

**Noise Isolation**: Motor and logic rails physically separated; star ground connection at PSU negative terminal only

### Motor Driver & Stepper Motor Control

**Architecture**: A4988 stepper drivers (×2) → NEMA 17 motors (Carousel + Conveyor 1)

**Per Driver**:

- **Inputs**: STEP (GPIO pin), DIR (GPIO pin), MS1/MS2 (microstepping mode select)
- **Power**: 12V + GND from primary rail
- **Current Limiting**: Onboard potentiometer calibrated for ~1.5A RMS per motor
- **Outputs**: Coil A± and B± to NEMA 17 stepper motor

**STM32 Firmware Tasks** (Phase 5.2 from BUILD.md):

1. Configure Timer TIM2 for carousel stepper control:
   - Frequency range 1–10 kHz (steps/sec adjustable from firmware)
   - Pulse generation via PWM channel with 50% duty cycle
2. Configure Timer TIM3 for conveyor stepper control: Same setup as TIM2
3. GPIO outputs for DIR pins: Set high/low to control direction (forward/reverse)
4. `home_carousel()` routine: Rotate until A3144 hall-effect sensor triggers, reset step counter to 0
5. `rotate_to_slot(index)` routine: Calculate steps from current position to target slot (36°/slot = X steps at configured frequency)

**Tuning Parameters** (to be determined during mechanical testing):

- Steps per full rotation (200 or 400, motor dependent)
- Microstepping mode (full, half, quarter, eighth step)
- Maximum frequency (limited by motor torque and load)
- Acceleration/deceleration ramp-up/ramp-down time

**Wiring Convention**:

```bash
PS (+12V) ──→ |A4988| ← STEP/DIR from STM32 GPIO
GND ──────────|||||── Stepper Coils (A+, A-, B+, B-)
```

### Solenoid Lock Control via MOSFET

**Architecture**: IRLZ44N MOSFET (logic-level, N-channel) as high-side driver for 12V solenoid

**Solenoid Specifications** (typical 12V latch-hold type):

- Activation voltage: 12V DC ±10%
- Hold current: ~500mA (continuous)
- Fail-secure: Spring return to locked position on de-energization

**MOSFET Gate Drive**:

- Gate pin connected to STM32 GPIO output (3.3V high = MOSFET ON, solenoid energized)
- Source connected to 12V primary rail (-)
- Drain connected to solenoid terminal
- Solenoid other terminal to 12V rail (+)
- Flywheel diode (1N4007, cathode to source) across solenoid to clamp back-EMF on de-energization

**STM32 GPIO Configuration**:

- Pin PA3 (or equivalent) configured as digital output
- Set high (3.3V) to energize solenoid → door LOCKED
- Set low (0V) to de-energize solenoid → door spring-returns to UNLOCKED

**Safety Interlocks**:

- Door-open IR sensor (GPIO interrupt with high priority) immediately sets solenoid GPIO low on interrupt
- Cannot be overridden by normal firmware logic — hardware interrupt handler always wins

**Wiring**:

```bash
12V (+) ───────────────→ Solenoid(+)

12V (-) → |IRLZ44N MOSFET|
   [Flywheel Diode: 1N4007]
   [Junction: Solenoid(-)]

STM32 GPIO PA3 ────→ MOSFET Gate (through 1kΩ resistor for protection)
```

### Hall-Effect Sensor Integration

**Sensor**: A3144 (or equivalent), 3-pin (GND, Vcc, OUT—open-collector)

**Purpose**: Absolute home reference for carousel homing routine; placed at slot 0 position with neodymium magnet ring on carousel

**Electrical**:

- Vcc (2.7–5.5V logic supply) connected to 5V logic rail through 100Ω protection resistor
- OUT (open-collector output) pulled high via 10kΩ resistor to 3.3V
- STM32 GPIO configured as digital input + edge-triggered interrupt (rising edge = sensor active)

**Signal Conditioning**:

- Software debounce: 50ms delay after sensor trigger before accepting signal (filters mechanical bounce)
- Interrupt priority: Medium (lower than door-open IR, higher than encoder polling)

**Firmware Routine** (`home_carousel()`):

1. Issue N steps at known frequency toward homing position
2. Wait for hall-effect interrupt (timeout after 5 seconds → error condition)
3. On interrupt: Stop motor immediately, reset step counter to 0, store as home position
4. Return success and new step offset value

**Wiring**:

```bash
5V Logic Rail → [100Ω] ──→ Vcc (A3144)
GND ────────→ GND (A3144)
Out (A3144) ──[100Ω]──→ STM32 GPIO PB4 (with 50ms software debounce)
         └──[10kΩ pull-up to 3.3V]
```

### Servo Motor Control (SG90 Servos ×2)

**Servos**: SG90 analog servos for card ejector flap (front gate) and expired card latch (side slot)

**Control Signal**: PWM at 50 Hz, 1–2ms pulse width

- 1.0ms pulse → 0° (fully CCW)
- 1.5ms pulse → 90° (center)
- 2.0ms pulse → 180° (fully CW)

**STM32 Firmware**:

- Configure Timer TIM4 Channel 1 & 2 as PWM output
- Frequency: 50 Hz (20ms period)
- Pulse width register: 1000–2000 counts (at 1µs clock granularity) to map to 1–2ms

**Wiring**:

```bash
5V Logic Rail ──→ Vcc (SG90)
GND ────────────→ GND (SG90)
STM32 PB6 (PWM) ──→ Signal (SG90)
```

### Raspberry Pi → STM32 SPI Communication

**Bus Specification**: SPI1, 1 MHz clock, Mode 0 (CPOL=0, CPHA=0)

**Raspberry Pi (Master)**:

- GPIO23 (SCLK) → STM32 PA5 (SPI1_SCK)
- GPIO24 (MOSI) → STM32 PA7 (SPI1_MOSI)
- GPIO25 (MISO) → STM32 PA6 (SPI1_MISO)
- GPIO8 (CE0) → STM32 PA4 (SPI1_NSS, active low)

**Command Frame Format** (Pi → STM32):

```bash
[COMMAND_BYTE] [PARAMETER_BYTE] [CHECKSUM_BYTE]
```

**Response Frame Format** (STM32 → Pi):

```bash
[STATUS_BYTE] [DATA_BYTE] [CHECKSUM_BYTE]
```

**Checksum Algorithm**: CRC-8 (polynomial 0xD5, simplest variant sufficient for local SPI)

**Command Set** (Phase 5 from BUILD.md Phase 4.4):

- `0x01`: ROTATE_TO_SLOT(slot_index) → rotate carousel to slot, return status
- `0x02`: EJECT_CARD() → pulse ejector servo, return status
- `0x03`: LATCH_CARD() → close expired card slot latch, return status
- `0x04`: UNLOCK_DOOR() → de-energize solenoid, return status
- `0x05`: LOCK_DOOR() → energize solenoid, return status
- `0x06`: GET_SENSOR_STATE() → read all 5 sensor states (packed byte), return status + sensor_byte
- `0x07`: HOME_CAROUSEL() → rotate until hall-effect triggers, reset step counter, return status

**Python SPI Driver** (Pi-side, from BUILD.md Phase 4.5):

- Module: `modules/spi_master.py`
- Function: `send_command(cmd_byte, param_byte)` → builds 3-byte frame, transfers, reads response, validates checksum
- Wrapper functions: `rotate_to_slot(index)`, `eject_card()`, `unlock_door()`, etc.
- Error handling: Timeout (>500ms response) = retry up to 3 times, then log failure

**Sample Wiring Diagram**:

```bash
Raspberry Pi 5              SPI Bus              STM32 Nucleo-F401RE
┌──────────────┐           (1 MHz)              ┌─────────────────┐
│ GPIO23 ─────────────────────────→ PA5 (SCK)   │                 │
│ GPIO24 ─────────────────────────→ PA7 (MOSI)  │                 │
│ GPIO25 ←─────────────────────── PA6 (MISO)   │                 │
│ GPIO8  ─────────────────────────→ PA4 (NSS)   │                 │
│ GND    ─────────────────────────→ GND         │                 │
└──────────────┘                                 └─────────────────┘
```

### Integration Checkpoint (Phase 5.1-5.7)

Before moving to full system integration, validate in sequence:

1. **Power Rails** (Phase 5 Task TBD): Verify 12V and 5V outputs under load; check for noise/ripple
2. **Stepper Drivers** (Phase 5.2): Test rotation in both directions; measure current draw at configured frequency
3. **Solenoid** (Phase 5.3 TBD): Confirm door lock/unlock with GPIO control; verify fail-secure on power loss
4. **Hall-Effect Homing** (Phase 5.2): Rotate carousel until home sensor triggers; confirm repeatability
5. **Servo Control** (Phase 5.3 TBD): Command servo through full range; measure response time
6. **SPI Loopback** (Phase 5.1.4): Echo all commands from Pi and confirm byte-for-byte round-trips
7. **Full Carousel Cycle**: Load a test card into Slot 0, rotate through all 10 positions, return to home — verify mechanical precision

**Documentation Reference**: See `firmware/` directory for STM32 CubeIDE project with complete HAL configuration and interrupt handlers.
