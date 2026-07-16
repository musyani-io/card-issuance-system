#!/usr/bin/env python3
"""SPI helpers for sending status frames to the lower controller."""

from __future__ import annotations
import argparse
import spidev

SPI_BUS = 0
SPI_DEVICE = 0
SPI_SPEED_HZ = 100000
SPI_MODE = 0


def send_spi_message(message: str) -> list[int]:
    """Send a short ASCII SPI message and immediately release the bus file descriptor."""
    if not message:
        raise ValueError("SPI message cannot be empty")

    payload = [ord(char) for char in message]
    
    spi = spidev.SpiDev()
    try:
        spi.open(SPI_BUS, SPI_DEVICE)
        spi.max_speed_hz = SPI_SPEED_HZ
        spi.mode = SPI_MODE
        return spi.xfer2(payload)
    finally:
        spi.close()  # Instantly release /dev/spidev0.0 for other concurrent processes


def send_status(success: bool, slot_index: int | None = None, is_ui: bool = False) -> str:
    """Send the card-processing status frame expected by the lower controller.
    
    UI transactions (is_ui=True):
        - Success: "2X" (where X is slot_index)
        - Failure: "FF"
        
    OCR transactions (is_ui=False):
        - Success: "1X" (where X is slot_index)
        - Failure: "00"
    """
    if is_ui:
        if success:
            if slot_index is None:
                raise ValueError("slot_index is required for a successful SPI status")
            frame = f"2{int(slot_index)}"
        else:
            frame = "FF"
    else:
        if success:
            if slot_index is None:
                raise ValueError("slot_index is required for a successful SPI status")
            frame = f"1{int(slot_index)}"
        else:
            frame = "00"

    send_spi_message(frame)
    return frame


def main() -> int:
    parser = argparse.ArgumentParser(description="SPI Master CLI utility.")
    parser.add_argument(
        "-c", "--command", 
        type=str, 
        required=True, 
        help="ASCII command string to send over SPI"
    )
    args = parser.parse_args()

    try:
        sent = send_spi_message(args.command)
        print(f"Sent command: {args.command} -> {sent}")
    except Exception as exc:
        print(f"SPI transmission failed: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())