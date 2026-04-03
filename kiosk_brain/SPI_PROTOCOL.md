# SPI Communication Protocol: Raspberry Pi 5 ↔ STM32 Nucleo-F401RE

## Overview

Defines byte-level protocol for Pi-to-STM32 communication over SPI bus at 1 MHz.
Every message is 3 bytes: [command/status, parameter/data, checksum].
Checksum is XOR of first two bytes to detect 1-bit corruption.

## Physical Interface

- Bus: SPI1 (GPIO10=MOSI, GPIO9=MISO, GPIO11=SCLK, GPIO8=CS)
- Speed: 1 MHz (stable over ~2m ribbon cable)
- Frame: 3 bytes per command, 3 bytes per response

## Command Frame Format

```bash
Byte 0 [CMD]:     Command code (0x10–0x41, see table)
Byte 1 [PARAM]:   Parameter (slot index, etc.) or 0x00
Byte 2 [CHECKSUM]: XOR(CMD ^ PARAM)
```

Example: Rotate to slot 5 → `[0x10, 0x05, 0x15]`

## Response Frame Format

```bash
Byte 0 [STATUS]:   Response code (0x00–0x04, see table)
Byte 1 [DATA]:     Payload (sensor flags, error detail, etc.)
Byte 2 [CHECKSUM]: XOR(STATUS ^ DATA)
```

## Command Code Table

| Hex  | Command          | Param Meaning    | Response       |
| ---- | ---------------- | ---------------- | -------------- |
| 0x10 | ROTATE_TO_SLOT   | Slot index (0–9) | ACK / BUSY     |
| 0x11 | EJECT_CARD       | (unused, 0x00)   | ACK / ERROR    |
| 0x12 | LATCH_CARD       | (unused, 0x00)   | ACK / ERROR    |
| 0x13 | RELEASE_LATCH    | (unused, 0x00)   | ACK / ERROR    |
| 0x20 | LOCK_DOOR        | (unused, 0x00)   | ACK / ERROR    |
| 0x21 | UNLOCK_DOOR      | (unused, 0x00)   | ACK / ERROR    |
| 0x30 | FEED_CARD        | (unused, 0x00)   | ACK / BUSY     |
| 0x31 | DIVERT_REJECT    | (unused, 0x00)   | ACK / ERROR    |
| 0x40 | GET_SENSOR_STATE | (unused, 0x00)   | SENSOR_PAYLOAD |
| 0x41 | HOME_CAROUSEL    | (unused, 0x00)   | ACK / BUSY     |

## Response Code Table

| Hex  | Response             | Data Byte Meaning                        |
| ---- | -------------------- | ---------------------------------------- |
| 0x00 | ACK                  | Operation complete                       |
| 0x01 | NACK                 | Command not recognized or invalid param  |
| 0x02 | BUSY                 | Motor/servo still moving; retry in 100ms |
| 0x03 | SENSOR_STATE_PAYLOAD | Packed sensor flags (see below)          |
| 0x04 | ERROR                | Hardware failure (motor stall, etc.)     |

## Sensor State Payload (Data byte for RESP_SENSOR_STATE_PAYLOAD)

```bashs
Bit 7 [Door Open]         : 1 = rear door unlocked/open
Bit 6 [Card at Rear Gate] : 1 = card at carousel entry sensor
Bit 5 [Card at Front Gate]: 1 = card at ejection slot
Bit 4 [Card in Reject]    : 1 = card in reject bin
Bits 3–0 [Reserved]       : Always 0
```

Example: `0b01010000` = Card at both rear and front gates

## Error Handling

**Checksum Failure:** STM32 rejects frame; Pi times out after 10ms and retries (max 3 times).
**Hardware Error:** STM32 responds with `RESP_ERROR`; Pi logs to audit_log and shows ErrorScreen.
