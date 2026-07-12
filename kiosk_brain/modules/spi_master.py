"""SPI helpers for sending status frames to the lower controller."""

from __future__ import annotations

from contextlib import suppress

import spidev


SPI_BUS = 0
SPI_DEVICE = 0
SPI_SPEED_HZ = 100000
SPI_MODE = 0


def send_spi_message(message: str) -> list[int]:
    """Send a short ASCII SPI message and return the transferred bytes.

    The lower controller currently expects the two-byte status frames used by
    the OCR pipeline, such as ``00`` for failure and ``1X`` for success.
    """

    if not message:
        raise ValueError("SPI message cannot be empty")

    spi = spidev.SpiDev()
    try:
        spi.open(SPI_BUS, SPI_DEVICE)
        spi.max_speed_hz = SPI_SPEED_HZ
        spi.mode = SPI_MODE
        payload = [ord(char) for char in message]
        return spi.xfer2(payload)
    finally:
        with suppress(Exception):
            spi.close()


def send_status(success: bool, slot_index: int | None = None) -> str:
    """Send the card-processing status frame expected by the lower controller."""

    frame = "00"
    if success:
        if slot_index is None:
            raise ValueError("slot_index is required for a successful SPI status")
        frame = f"1{int(slot_index)}"

    send_spi_message(frame)
    return frame


def main() -> int:
    try:
        sent = send_spi_message("A")
        print(f"Sent: A -> {sent}")
    except Exception as exc:
        print(f"SPI test failed: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())