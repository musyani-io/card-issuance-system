#!/usr/bin/env python3
"""
SPI Loopback Test: Pi sends ECHO command to STM32, receives response.
Command: [0x42 (ECHO), 0x55 (param), 0x17 (checksum)]
Expected respo
"""

import spidev
import time
import sys

# SPI configuration
BUS = 0
DEVICE = 0
SPEED = 1000000  # 1 MHz (same as STM32 firmware)

# Command bytes
CMD_ECHO = 0x42
PARAM_TEST = 0x55

def calculate_checksum(cmd, param):
    """Calculate XOR checksum."""
    return cmd ^ param

def main():
    spi = spidev.SpiDev()
    
    try:
        spi.open(BUS, DEVICE)
        spi.max_speed_hz = SPEED
        spi.mode = 0
        
        print(f"✓ SPI opened: /dev/spidev{BUS}.{DEVICE} at {SPEED/1e6:.1f} MHz")
        print(f"Sending 5 commands in sequence...\n")
        
        # Send ECHO command 5 times
        success_count = 0
        for i in range(5):
            checksum = calculate_checksum(CMD_ECHO, PARAM_TEST)
            cmd_frame = [CMD_ECHO, PARAM_TEST, checksum]
            
            print(f"[{i+1}] → Sending: {[hex(b) for b in cmd_frame]}")
            response = spi.xfer2(cmd_frame)
            print(f"[{i+1}] ← Received: {[hex(b) for b in response]}")
            
            if response == cmd_frame:
                print(f"[{i+1}] ✓ MATCH\n")
                success_count += 1
            else:
                print(f"[{i+1}] ✗ MISMATCH\n")
        
        print(f"Result: {success_count}/5 successful")
        return 0 if success_count == 5 else 1
        
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return 1
    finally:
        spi.close()
        print("✓ SPI closed")

if __name__ == "__main__":
    sys.exit(main())
