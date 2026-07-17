# SPI Communication Protocol: Raspberry Pi 5 ↔ Arduino Mega 2560

## Overview

Defines the ASCII-level protocol for Raspberry Pi 5 to Arduino Mega 2560 communication over the SPI bus at 100 kHz.
Every transmission is exactly 2 characters (2 bytes) of ASCII data, terminated by a null character in the receiver buffer. No checksum bytes or complex frame overhead is used in this prototype.

---

## Physical Interface

- **Raspberry Pi 5 (Master)**:
  - Bus: SPI0 (GPIO 11 = SCK, GPIO 10 = MOSI, GPIO 9 = MISO, GPIO 8 = CE0)
  - Speed: 100 kHz (configured in `spi_master.py`)
  - Mode: SPI Mode 0 (CPOL=0, CPHA=0)
- **Arduino Mega 2560 (Slave)**:
  - Pins: SS (53), MOSI (51), MISO (50), SCK (52)
  - Common Ground: A shared common ground reference point must be established between both boards.
  - Logic Level Shift: A logic level shifter must be used on the MISO line (5V to 3.3V) to protect the Pi.

---

## Transmission Frame Format

Commands sent by the Raspberry Pi are 2-character ASCII strings. The Arduino Mega reads the 2 bytes, terminates them as a string, and processes the corresponding routing routine.

```text
Byte 0: Command Group / Transaction Prefix ('0', '1', '2', 'F')
Byte 1: Target slot index ('0', '1', '2') or command identifier ('0', 'F')
```

---

## Command Reference Table

The following status and command frames are sent by the Raspberry Pi `spi_master.py`:

| ASCII Frame | Transaction Type | Action / Target Meaning |
| ----------- | ---------------- | ----------------------- |
| `"10"`      | Ingestion (OCR)  | Route Compartment A to Entrance (0°) and trigger servo release |
| `"11"`      | Ingestion (OCR)  | Route Compartment B to Entrance (120°) and trigger servo release |
| `"12"`      | Ingestion (OCR)  | Route Compartment C to Entrance (240°) and trigger servo release |
| `"00"`      | Ingestion (OCR)  | OCR Error/Failure: Route Compartment C to Entrance (240°) |
| `"20"`      | Collection (UI)  | Route Compartment A to Exit (180°) and await pickup |
| `"21"`      | Collection (UI)  | Route Compartment B to Exit (300°) and await pickup |
| `"FF"`      | Collection (UI)  | UI Transaction Failure / Cancelled |

---

## Error and Status Handling

- **Invalid Command**: The Arduino Mega logs "Unknown SPI Frame" via its serial monitor on baud 115200 if the received 2-byte frame does not match any known commands.
- **SS Pin Synchronization**: The Mega's software buffer index resets whenever the Chip Select (SS) line goes HIGH (signaling that the Pi has released the SPI bus), which automatically maintains word synchronization.
