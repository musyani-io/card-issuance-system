import time 
import spidev

spi = spidev.SpiDev()

spi.open(0, 0)

spi.max_speed_hz = 100000
spi.mode = 0

try: 
    while True:
        data = ord('A')
        spi.xfer2([data])

        print("Sent: ", chr(data))
        time.sleep(1)

except KeyboardInterrupt:
    spi.close()
    print("SPI closed")