"""SPI helpers for sending status frames to the lower controller."""

from __future__ import annotations
import spidev

SPI_BUS = 0
SPI_DEVICE = 0
SPI_SPEED_HZ = 100000
SPI_MODE = 0

# Persistent SPI singleton instance
_spi_instance: spidev.SpiDev | None = None

def _get_spi_bus() -> spidev.SpiDev:
    """Lazy initialize and keep the SPI connection open."""
    global _spi_instance
    if _spi_instance is None:
        _spi_instance = spidev.SpiDev()
        _spi_instance.open(SPI_BUS, SPI_DEVICE)
        _spi_instance.max_speed_hz = SPI_SPEED_HZ
        _spi_instance.mode = SPI_MODE
    return _spi_instance

def send_spi_message(message: str) -> list[int]:
    """Send a short ASCII SPI message using the persistent connection."""
    if not message:
        raise ValueError("SPI message cannot be empty")

    spi = _get_spi_bus()
    payload = [ord(char) for char in message]
    return spi.xfer2(payload)

def send_status(success: bool, slot_index: int | None = None) -> str:
    """Send the card-processing status frame expected by the lower controller."""
    frame = "00"
    if success:
        if slot_index is None:
            raise ValueError("slot_index is required for a successful SPI status")
        frame = f"1{int(slot_index)}"

    send_spi_message(frame)
    return frame