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
