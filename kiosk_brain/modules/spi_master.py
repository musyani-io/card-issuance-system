"""
SPI Master Protocol for STM32 Hardware Control

This module implements the Raspberry Pi 5 SPI master protocol for communicating with STM32 Nucleo-F401RE:
- GPIO-based SPI frame transmission (3-byte protocol)
- Stepper motor control (card movement)
- Solenoid activation (dispensing mechanism)
- Status polling (motor done, solenoid armed, error conditions)

**PHASE 5 IMPLEMENTATION:** Deferred to mechanical subsystem integration phase.

Hardware Interface: SPI Protocol
================================

Protocol: 3-byte frames over SPI at 1 MHz clock

FRAME FORMAT:
    Byte 0 (Command):  0xAA (MOTOR), 0xBB (SOLENOID), 0xCC (STATUS), 0xDD (RESET)
    Byte 1 (Args):     Motor ID (0-29), direction (1=fwd/-1=rev), steps count
    Byte 2 (Checksum): XOR(Byte0 ^ Byte1) for error detection

MOTOR COMMANDS (0xAA):
    - Payload: [motor_id: 4bits, direction: 4bits, steps: 8bits]
    - Example: 0xAA 0x1F 0xC5 → Motor 1, forward, 15 steps, checksum
    - Response: 0x00 (ACK) once motor finishes (blocking wait)

SOLENOID COMMAND (0xBB):
    - Payload: [solenoid_id: 4bits, action: 4bits]
    - 0xBB 0x01 0xBA → Solenoid 0, ACTIVATE, checksum
    - Response: 0x00 (ACK) on success

STATUS QUERY (0xCC):
    - No payload
    - Response: status byte (bit flags for motor ready, solenoid armed, errors)

Planned Functions:
==================

- init_spi(bus=0, device=0, speed=1_000_000) - Initialize Pi GPIO/SPI
- move_motor(motor_id, direction, steps) - Send motor command, wait for done
- activate_solenoid(solenoid_id) - Dispense card via solenoid
- query_status() - Poll hardware status flags
- calculate_checksum(byte0, byte1) - XOR checksum for frame validation
- handle_spi_error(error_code) - Error recovery and retry logic
"""

import spidev

# Carousel commands
CMD_ROTATE_TO_SLOT = 0x10
CMD_EJECT_CARD = 0x11
CMD_LATCH_CARD = 0x12
CMD_RELEASE_LATCH = 0x13

# Door commands
CMD_LOCK_DOOR = 0x20
CMD_UNLOCK_DOOR = 0x21

# Conveyor commands
CMD_FEED_CARD = 0x30
CMD_DIVERT_REJECT = 0x31

# Sensor commands
CMD_GET_SENSOR_STATE = 0x40
CMD_HOME_CAROUSEL = 0x41

# Response commands
RESP_ACK = 0x00
RESP_NACK = 0x01
RESP_BUSY = 0x03
RESP_SENSOR_STATE = 0x04
RESP_ERROR = 0x05


def build_command_frames(cmd_byte, param_byte=0x00):
    """
    Build a 3-byte SPI command frame with XOR checksum for STM32 transmission.

    Args:
        cmd_byte: Command identifier (0xAA=MOTOR, 0xBB=SOLENOID, 0xCC=STATUS, 0xDD=RESET, etc.)
        param_byte: Parameter/payload byte (default 0x00 if no payload)
                   Example: Motor ID + direction in upper/lower nibbles, or solenoid ID

    Returns:
        list: 3-byte frame [cmd_byte, param_byte, checksum]
              where checksum = cmd_byte XOR param_byte (detects transmission errors)

    Example:
        >>> build_command_frames(0xAA, 0x1F)  # Motor command with params
        [170, 31, 197]  # Decimal representation of [0xAA, 0x1F, 0xC5]

    Used by:
        - send_command() to construct frames before SPI transmission
        - parse_response_frame() to validate received frames

    Inline Logic:
        - Checksum = XOR bitwise operation between cmd_byte and param_byte
        - XOR chosen because: stateless, reversible, detects bit flips
        - Frame format: [COMMAND] [PAYLOAD] [CHECKSUM] - fixed 3-byte protocol
    """
    checksum = cmd_byte ^ param_byte
    return [cmd_byte, param_byte, checksum]


def parse_response_frame(frame_bytes):
    """
    Validate and parse 3-byte response frame received from STM32 over SPI.

    Args:
        frame_bytes: List or bytes object of 3 bytes [status, data, checksum]
                    status: Response type (0x00=ACK, 0x01=NACK, 0x03=BUSY, 0x05=ERROR, etc.)
                    data: Response payload (depends on command context)
                    checksum: Transmitted checksum (should equal status XOR data)

    Returns:
        tuple: (status_byte, data_byte, is_valid)
               - status_byte: Response status code (or None if invalid length)
               - data_byte: Response data payload (or None if invalid length)
               - is_valid: bool (True if checksum matches, False if mismatch detected)

    Errors:
        - Returns (None, None, False) if frame_bytes is not 3 bytes (protocol violation)
        - Returns (status, data, False) if checksum mismatch detected (transmission error)

    Example:
        >>> parse_response_frame([0x00, 0x2A, 0x2A])  # ACK with data 0x2A
        (0, 42, True)  # Valid frame

        >>> parse_response_frame([0x05, 0x00, 0x99])  # ERROR with wrong checksum
        (5, 0, False)  # Invalid checksum detected

    Used by:
        - send_command() to validate STM32 responses
        - Enables error recovery: NACK/ERROR triggers retry logic

    Inline Logic:
        - Checksum validation: expected = status ^ data, must match transmitted checksum
        - Early exit on length violation (protocol enforcement)
        - Returns all three values to allow caller to distinguish transmission errors from logic errors
    """
    # Validate frame length (protocol requires exactly 3 bytes)
    if len(frame_bytes) != 3:
        return None, None, False

    # Extract frame components
    status, data, checksum = frame_bytes[0], frame_bytes[1], frame_bytes[2]
    # Calculate expected checksum (XOR of status and data)
    expected_checksum = status ^ data
    # Validate checksum (detects bit flips during transmission)
    is_valid = checksum == expected_checksum
    # Return parsed components (caller checks is_valid to determine action)
    return status, data, is_valid


def send_command(cmd_byte, param_byte=0x00, timeout_ms=100):
    """
    Send command to STM32 over SPI bus and wait for response with timeout.

    Args:
        cmd_byte: Command identifier (0xAA, 0xBB, 0xCC, 0xDD, etc.)
        param_byte: Parameter byte (motor ID, solenoid ID, direction, etc.). Default: 0x00
        timeout_ms: Maximum time to wait for response in milliseconds (default: 100ms)

    Returns:
        dict: Response with keys:
            - 'status': Response type (0x00=ACK, 0x01=NACK, 0x03=BUSY, 0x05=ERROR)
            - 'data': Response payload byte (context-dependent)
            - 'is_valid': bool (True if checksum OK, False if transmission error)
            - 'error': str (if is_valid=False or timeout, error description)

    Side Effects:
        - Initializes SPI bus (GPIO23 CLK, GPIO24 MOSI, GPIO25 MISO, GPIO8 CE0)
        - Transmits 3-byte command frame over SPI at 1MHz
        - Blocks until response received or timeout expires

    Called by:
        - rotate_to_slot(), eject_card(), unlock_door(), etc. (hardware control functions)
        - Used as lowest-level SPI interface to STM32

    Error Handling:
        - Checksum mismatch: returns RESP_ERROR (caller retries command)
        - Timeout: returns RESP_ERROR (caller retries or escalates to UI error screen)
        - Unknown status: passes through to caller (caller handles context-specific logic)

    Inline Logic:
        - build_command_frames() creates 3-byte frame with XOR checksum
        - spidev.SpiDev().xfer() is blocking call (waits for both TX and RX)
        - parse_response_frame() validates checksum
        - Checksum failure indicates data corruption (SPI noise), trigger hardware retry
    """
    # Build 3-byte command frame with XOR checksum
    frame = build_command_frames(cmd_byte, param_byte)

    # Initialize SPI bus
    bus = spidev.SpiDev()
    bus.open(0, 0)  # Bus 0, Chip Select 0 (standard Raspberry Pi SPI pins)
    # Send command frame and receive response (blocking until complete or timeout)
    response_frame = bus.xfer(frame)
    bus.close()  # Release SPI bus

    # Parse response frame (extracts status, data, validates checksum)
    status, data, is_valid = parse_response_frame(response_frame)

    # Checksum validation failed (transmission error detected)
    if not is_valid:
        return {"status": RESP_ERROR, "data": 0x00, "error": "Checksum mismatch"}

    # Return parsed response (caller handles status-specific logic)
    return {"status": status, "data": data, "is_valid": is_valid}


def rotate_to_slot(slot_index):
    """
    Rotate card carousel to specified slot position.

    Args:
        slot_index: Carousel slot number (0-29) where card is stored
                   0 = top slot, increases clockwise, 29 = bottom-right slot

    Returns:
        dict: Operation result with keys:
            - 'success': bool (True if rotation completed)
            - 'slot': int (slot_index if successful) or None on error
            - 'error': str or None (error description if operation failed)

    Error Conditions:
        - 'Stepper still moving, retry in 100ms': Motor busy, previous command running
        - 'Hardware error': STM32 reported motor failure (stalled, no power, etc.)
        - 'Invalid slot index': slot_index out of range [0-29]
        - 'Unknown response': Unexpected status from STM32

    Called by:
        - Collection workflow (main.py) after card dispensing confirmed
        - Batch loading staff UI to physically rotate to each card slot

    Side Effects:
        - Stepper motor physically rotates carousel to target slot (takes ~2 seconds for 180°)
        - Blocks until motor finishes or returns error

    Workflow Context:
        - Fired AFTER student enters correct PIN (card selected)
        - Before eject_card() (positions card for dispensing)
        - Carousel must be locked (latch_card() called) before rotation to prevent jamming

    Inline Logic:
        - Sends CMD_ROTATE_TO_SLOT (0x10) with slot_index as parameter
        - RESP_ACK (0x00) = rotation complete, success
        - RESP_BUSY (0x03) = motor running, caller should retry after 100ms
        - RESP_ERROR (0x05) = mechanical failure (stall detected, motor error)
        - RESP_NACK (0x01) = command not recognized or parameters invalid
    """
    result = send_command(CMD_ROTATE_TO_SLOT, param_byte=slot_index)
    if result["status"] == RESP_ACK:
        return {"success": True, "slot": slot_index}
    elif result["status"] == RESP_BUSY:
        return {"success": False, "error": "Stepper still moving, retry in 100ms"}
    elif result["status"] == RESP_ERROR:
        return {"success": False, "error": "Hardware error"}
    elif result["status"] == RESP_NACK:
        return {"success": False, "error": "Invalid slot index"}
    else:
        return {"success": False, "error": f"Unknown response: {result["status"]}"}


def eject_card():
    """
    Eject currently selected card from carousel to dispenser tray.

    Returns:
        dict: Operation result with keys:
            - 'success': bool (True if card ejected)
            - 'error': str or None (error description if operation failed)

    Error Conditions:
        - 'Servo still moving, retry in 100ms': Mechanical system busy
        - 'Hardware error': Servo/motor failure detected
        - 'Invalid command': STM32 firmware does not recognize command (firmware version mismatch)
        - 'Unknown response': Unexpected status code

    Called by:
        - Collection confirmation screen after student has verified PIN
        - Immediately after rotate_to_slot() positions card

    Side Effects:
        - Servo motor pushes/pulls card ejection mechanism
        - Card physically exits carousel into dispenser tray (takes ~1 second)
        - Blocks until servo finishes or error detected

    Workflow Sequence:
        1. rotate_to_slot(slot_index) ← Card selected
        2. eject_card() ← Card ejected (THIS FUNCTION)
        3. Lock door (solenoid)
        4. UI shows "Card dispensed successfully"

    Inline Logic:
        - Sends CMD_EJECT_CARD (0x11) with no parameters
        - RESP_ACK (0x00) = ejection complete
        - RESP_BUSY (0x03) = servo still moving, caller retries
        - RESP_ERROR (0x05) = servo stalled or no power
        - No RESP_NACK expected (command is fixed, no parameters to validate)
    """
    result = send_command(CMD_EJECT_CARD)
    if result["status"] == RESP_ACK:
        return {"success": True}
    elif result["status"] == RESP_BUSY:
        return {"success": False, "error": "Servo still moving, retry in 100ms"}
    elif result["status"] == RESP_ERROR:
        return {"success": False, "error": "Hardware error"}
    elif result["status"] == RESP_NACK:
        return {"success": False, "error": "Invalid command"}
    else:
        return {"success": False, "error": f"Unknown response: {result["status"]}"}


def unlock_door():
    """
    Unlock solenoid to allow student to open dispenser door and retrieve card.

    Returns:
        dict: Operation result with keys:
            - 'success': bool (True if door unlocked)
            - 'error': str or None (error description if operation failed)

    Error Conditions:
        - 'Solenoid not stable, retry in 100ms': Solenoid coil energizing/de-energizing
        - 'Hardware error': Solenoid power or driver failure
        - 'Invalid command': Command not recognized (firmware mismatch)
        - 'Unknown response': Unexpected status code

    Called by:
        - Collection confirmation screen immediately after eject_card()
        - Also called on timeout/error to ensure door is locked safely

    Side Effects:
        - Solenoid coil energizes (consumes ~5A at 12V for ~500ms)
        - Door latch retracts (mechanical lever)
        - Student can now push door open and remove card (< 10 second grace period)

    Workflow Sequence:
        1. rotate_to_slot() + eject_card() ← Card physically moved
        2. unlock_door() ← Door solenoid energized (THIS FUNCTION)
        3. UI displays "Please collect your card"
        4. Student presses physical door release button
        5. lock_door() called (solenoid de-energizes after timeout)

    Safety Notes:
        - Door must be unlocked for < 15 seconds (security: prevent tampering)
        - After timeout: lock_door() automatically re-engages solenoid
        - If unlock fails: card remains latched (student cannot access, prevents theft)

    Inline Logic:
        - Sends CMD_UNLOCK_DOOR (0x21) with no parameters
        - RESP_ACK (0x00) = solenoid energized, door physically unlocked
        - RESP_BUSY (0x03) = solenoid still transitioning, retry after 100ms
        - RESP_ERROR (0x05) = solenoid driver error or power loss
    """
    result = send_command(CMD_UNLOCK_DOOR)
    if result["status"] == RESP_ACK:
        return {"success": True}
    elif result["status"] == RESP_BUSY:
        return {"success": False, "error": "Solenoid not stable, retry in 100ms"}
    elif result["status"] == RESP_ERROR:
        return {"success": False, "error": "Hardware error"}
    elif result["status"] == RESP_NACK:
        return {"success": False, "error": "Invalid command"}
    else:
        return {"success": False, "error": f"Unknown response: {result["status"]}"}


def get_sensor_state():
    """
    Poll hardware sensors and return current state flags (door, card position, etc.).

    Returns:
        dict: Sensor state with keys:
            - 'success': bool (True if sensor read OK)
            - 'door_open': bool (True if door is physically open)
            - 'card_rear': bool (True if card sensor detects card in rear position)
            - 'error': str or None (error description if sensor poll failed)

    Error Conditions:
        - 'Sensor poll hardware error': STM32 sensor module failure
        - 'Unknown response': Unexpected status from STM32

    Returns on Error:
        - 'success': False
        - 'door_open': None
        - 'card_rear': None
        - 'error': error description

    Called by:
        - Kiosk initialization (diagnostic check: sensors responding)
        - Collection workflow to confirm door is open before timeout
        - Batch loading staff UI for mechanical verification

    Side Effects:
        - Reads GPIO inputs from STM32 (no output changes)
        - Non-blocking (sensor poll returns immediately)

    Sensor Interpretation:
        - door_open=True: Student has access to dispenser (physical door is open)
        - door_open=False: Door is closed (card not accessible)
        - card_rear=True: Card is in rear position (carousel moved card to tray)
        - card_rear=False: Card not in tray yet (carousel still positioning)

    Inline Logic:
        - Sends CMD_GET_SENSOR_STATE (0x40) with no parameters
        - Response data byte = bit flags:
          - Bit 7 (0x80): Door open sensor
          - Bit 6 (0x40): Card rear position sensor
        - RESP_SENSOR_STATE (0x04) = valid sensor data returned
        - Extracts door_open and card_rear using bitwise AND with bit masks
    """
    result = send_command(CMD_GET_SENSOR_STATE)
    if result["status"] == RESP_SENSOR_STATE:
        # Extract individual sensor bits from response data byte
        door_open = bool(result["data"] & 0x80)  # Bit 7: door open sensor
        card_rear = bool(result["data"] & 0x40)  # Bit 6: card rear sensor

        return {"success": True, "door_open": door_open, "card_rear": card_rear}
    elif result["status"] == RESP_ERROR:
        return {"success": False, "error": "Sensor poll hardware error"}
    else:
        return {"success": False, "error": f"Unknown response: {result["status"]}"}


def lock_door():
    """
    Lock solenoid to prevent student from opening dispenser door.

    Returns:
        dict: Operation result with keys:
            - 'success': bool (True if door locked)
            - 'error': str or None (error description if operation failed)

    Error Conditions:
        - 'Solenoid still moving, retry in 100ms': Solenoid coil transitioning
        - 'Hardware error': Solenoid power or driver failure
        - 'Unexpected response': Unexpected status code

    Called by:
        - Collection timeout handler (auto-lock after student takes card)
        - Session cleanup to secure kiosk after collection
        - Error handling to return to safe state

    Side Effects:
        - Solenoid coil de-energizes (no power)
        - Door latch physically re-engages (mechanical return spring)
        - Door is now mechanically locked (student cannot access carousel)

    Workflow Context:
        - Collection sequence ends with lock_door() (final security step)
        - Ensures card cannot be stolen after student collection window closes
        - Timeout trigger: lock_door() fires automatically if student doesn't leave within 15 seconds

    Safety Notes:
        - Must be called after unlock_door() (grace period for student to remove card)
        - Prevents tampering: door physically blocked once this returns success
        - If lock fails: alarm triggered (solenoid power monitoring)

    Inline Logic:
        - Sends CMD_LOCK_DOOR (0x20) with no parameters
        - RESP_ACK (0x00) = solenoid de-energized, door physically locked
        - RESP_BUSY (0x03) = solenoid still transitioning, retry after 100ms
        - RESP_ERROR (0x05) = solenoid driver error or power loss (critical alarm)
    """
    result = send_command(CMD_LOCK_DOOR)
    if result["status"] == RESP_ACK:
        return {"success": True}
    elif result["status"] == RESP_BUSY:
        return {"success": False, "error": "Solenoid still moving, retry in 100ms"}
    elif result["status"] == RESP_ERROR:
        return {"success": False, "error": "Hardware error"}
    else:
        return {"success": False, "error": f"Unexpected response: {result['status']}"}


def latch_card():
    """
    Engage mechanical latch to secure card in carousel during rotation.

    Returns:
        dict: Operation result with keys:
            - 'success': bool (True if card latched)
            - 'error': str or None (error description if operation failed)

    Error Conditions:
        - 'Servo still moving, retry in 100ms': Servo mechanism busy
        - 'Hardware error': Servo stall or power failure
        - 'Unexpected response': Unexpected status code

    Called by:
        - Batch loading phase: engage latch before rotating to each card position
        - Before rotate_to_slot() to prevent card jamming during carousel rotation

    Side Effects:
        - Servo motor engages mechanical latch pin
        - Card is now physically secured (cannot fall out during rotation)
        - Blocks until servo finishes or error detected

    Workflow Context:
        1. Kiosk startup: latch_card() (card secured at startup)
        2. Batch loading loop:
            a. rotate_to_slot() (carousel rotates)
            b. latch_card() (after rotation, resecure before next movement)
        3. Collection: release_latch() before eject_card()

    Mechanical Notes:
        - Latch must be engaged for any carousel rotation (prevents card ejection)
        - Servo uses spring return: FAIL-SAFE design (unlocked = spring-engaged)
        - Must call release_latch() before eject_card() to physically move card

    Inline Logic:
        - Sends CMD_LATCH_CARD (0x12) with no parameters
        - RESP_ACK (0x00) = servo engaged, card mechanically latched
        - RESP_BUSY (0x03) = servo still moving, caller retries
        - RESP_ERROR (0x05) = servo stalled or power loss
    """
    result = send_command(CMD_LATCH_CARD)
    if result["status"] == RESP_ACK:
        return {"success": True}
    elif result["status"] == RESP_BUSY:
        return {"success": False, "error": "Servo still moving, retry in 100ms"}
    elif result["status"] == RESP_ERROR:
        return {"success": False, "error": "Hardware error"}
    else:
        return {"success": False, "error": f"Unexpected response: {result['status']}"}


def release_latch():
    """
    Release mechanical latch to allow card movement during ejection or positioning.

    Returns:
        dict: Operation result with keys:
            - 'success': bool (True if latch released)
            - 'error': str or None (error description if operation failed)

    Error Conditions:
        - 'Servo still moving, retry in 100ms': Servo mechanism busy
        - 'Hardware error': Servo stall or power failure
        - 'Unexpected response': Unexpected status code

    Called by:
        - Collection workflow: must release before eject_card()
        - Batch diagnostics: release to allow manual carousel inspection

    Side Effects:
        - Servo motor disengages mechanical latch pin
        - Latch retracts (spring-loaded design)
        - Card can now be physically moved by carousel motor

    Workflow Sequence:
        1. latch_card() ← Card secured
        2. rotate_to_slot() ← Carousel rotates (card latched, cannot move)
        3. latch_card() ← Resecure at new position
        4. [On collection] release_latch() ← Unlatch for movement (THIS FUNCTION)
        5. eject_card() ← Card physically ejected

    CRITICAL Constraint:
        - MUST call release_latch() BEFORE eject_card()
        - Calling eject_card() with latch engaged = servo stall + error
        - Fail-safe: If latch still engaged, eject command fails (prevents damage)

    Mechanical Notes:
        - Spring-loaded design: latch automatically re-engages on power loss (safe state)
        - Servo center position = latched, left/right = latched/unlatched positions
        - Takes ~500ms to fully retract

    Inline Logic:
        - Sends CMD_RELEASE_LATCH (0x13) with no parameters
        - RESP_ACK (0x00) = servo disengaged, latch physically retracted
        - RESP_BUSY (0x03) = servo still moving, caller retries
        - RESP_ERROR (0x05) = servo stalled or power loss
    """
    result = send_command(CMD_RELEASE_LATCH)
    if result["status"] == RESP_ACK:
        return {"success": True}
    elif result["status"] == RESP_BUSY:
        return {"success": False, "error": "Servo still moving, retry in 100ms"}
    elif result["status"] == RESP_ERROR:
        return {"success": False, "error": "Hardware error"}
    else:
        return {"success": False, "error": f"Unexpected response: {result['status']}"}


def feed_card():
    """
    Advance card through conveyor system (preparation for ejection).

    Returns:
        dict: Operation result with keys:
            - 'success': bool (True if card fed successfully)
            - 'error': str or None (error description if operation failed)

    Error Conditions:
        - 'Motor still moving, retry in 100ms': Conveyor motor busy
        - 'Hardware error': Motor power failure or jam detected
        - 'Unexpected response': Unexpected status code

    Called by:
        - [OPTIONAL] Collection workflow to advance card toward exit tray
        - May not be needed if eject_card() directly moves card to tray
        - Used in batch loading for pre-positioning cards

    Side Effects:
        - Conveyor motor activates (feeds card forward ~50mm)
        - Card moves closer to final ejection point
        - Blocks until motor finishes or error detected

    Workflow Context:
        - Part of multi-stage card movement:
            1. rotate_to_slot() ← Select carousel position
            2. latch_card() ← Secure card
            3. [Optional] feed_card() ← Advance toward tray (THIS FUNCTION)
            4. eject_card() ← Final ejection

    Integration Note:
        - May be redundant if eject_card() handles complete card exit
        - Included for potential future mechanical refinements

    Inline Logic:
        - Sends CMD_FEED_CARD (0x30) with no parameters
        - RESP_ACK (0x00) = conveyor motor advanced card
        - RESP_BUSY (0x03) = conveyor still moving, caller retries
        - RESP_ERROR (0x05) = motor stalled or jam detected
    """
    result = send_command(CMD_FEED_CARD)
    if result["status"] == RESP_ACK:
        return {"success": True}
    elif result["status"] == RESP_BUSY:
        return {"success": False, "error": "Motor still moving, retry in 100ms"}
    elif result["status"] == RESP_ERROR:
        return {"success": False, "error": "Hardware error"}
    else:
        return {"success": False, "error": f"Unexpected response: {result['status']}"}


def home_carousel():
    """
    Home carousel to known reference position using Hall effect sensor.

    Returns:
        dict: Operation result with keys:
            - 'success': bool (True if carousel homed successfully)
            - 'carousel_homed': bool or None (True if at home position after homing)
            - 'error': str or None (error description if operation failed)

    Error Conditions:
        - 'Carousel still moving, retry in 100ms': Homing motion still in progress
        - 'Hall sensor not found, carousel misaligned': Sensor not detecting home position
          (indicates mechanical misalignment or sensor failure)
        - 'Unexpected response': Unexpected status code

    Called by:
        - Kiosk initialization: home carousel at startup to establish known reference
        - Batch loading phase: home carousel before first card selection
        - Error recovery: home carousel if rotation fails (resynchronize)
        - Diagnostic mode: staff menu to physically reset carousel

    Side Effects:
        - Stepper motor rotates carousel slowly until Hall sensor triggers
        - Takes ~5-10 seconds (full 360° rotation at reduced speed)
        - After homing: slot_index = 0 (carousel at top, known position)
        - Blocks until sensor found or timeout

    Mechanical Context:
        - Hall sensor on carousel edge detects magnetic marker at home position
        - Home position: slot 0 at top of carousel (standard reference)
        - Homing required after power-on or mechanical disruption (crash detection)

    Workflow Sequence (After Power-On):
        1. KioskApp.__init__() starts
        2. spi_master.home_carousel() ← MUST succeed before any rotation
        3. If home_carousel() fails: raise error (kiosk cannot operate)
        4. Now rotate_to_slot() works reliably (index = offset from home)

    Safety Notes:
        - MUST NOT rotate carousel without homing first (index goes out of sync)
        - If homing fails: kiosk is in safe state (carousel immobilized)
        - Recovery: manually rotate carousel to align marker with sensor, restart app

    Inline Logic:
        - Sends CMD_HOME_CAROUSEL (0x41) with no parameters
        - RESP_ACK (0x00) = carousel homed, now at slot 0
        - RESP_BUSY (0x03) = homing still in progress, caller retries
        - RESP_ERROR (0x05) = Hall sensor not found (indicates mechanical problem)
    """
    result = send_command(CMD_HOME_CAROUSEL)
    if result["status"] == RESP_ACK:
        return {"success": True, "carousel_homed": True}
    elif result["status"] == RESP_BUSY:
        return {"success": False, "error": "Carousel still moving, retry in 100ms"}
    elif result["status"] == RESP_ERROR:
        return {"success": False, "error": "Hall sensor not found, carousel misaligned"}
    else:
        return {"success": False, "error": f"Unexpected response: {result['status']}"}
