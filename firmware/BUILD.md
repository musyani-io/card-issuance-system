# 🔌 STM32 Firmware Build & Integration Plan

> **Project:** Smart ID Card Distribution Kiosk — STM32F401RE Nucleo Control Unit  
> **Controller:** STM32 Nucleo-F401RE  
> **Stack:** STM32 HAL · C · STM32CubeMX · SPI Slave · TIM2/TIM4 PWM · GPIO  
> **Communication Protocol:** SPI 1 MHz, 3-byte frames with XOR checksum  
> **Actuators:** NEMA 17 stepper (carousel), 2× SG90 servo (latch & eject), solenoid (door lock)  
> **Sensors:** A3144 hall-effect (home reference), 4× IR break-beam (door, rear gate, front gate, reject bin)

---

## Phase 5 — STM32 Firmware & Mechanical Integration

> **Weeks:** 5–7 | **Estimated Total Time:** ~41.5 hours  
> **Goal:** Build firmware-first: scaffold the STM32 stack (SPI, timers, GPIOs), verify each subsystem in isolation (SPI, stepper, servo, sensors), then fabricate and integrate the mechanical hardware.  
> **Deliverable:** Fully integrated STM32 firmware responding to all SPI commands + functional carousel and conveyor with all 10 slot positions validated.  
> **Philosophy:** Firmware bring-up first (isolated on bench), then bolt on the mechanics. This allows you to debug the hard-to-debug first, before adding physical complexity.

```text
Progress  [░░░░░░░░░░░░░░░░░░░░]   0%
```

---

## Task 5.0 — Hardware Pin Map and CubeMX Planning

> _Before you touch CubeMX, freeze your hardware contract. Which STM32 pins will drive the SPI bus, stepper timer, servo PWM, solenoid, hall sensor, and IR sensors? Document this first so CubeMX generation doesn't force a redesign later._

**Context:**
The Nucleo-F401RE has 64 pins. Some are already used: PA2/PA3 (USART2), PA5 (LD2 LED), PC13 (button), PA13/PA14/PB3 (debug/SWD). The STM32 also has specific peripheral assignments by hardware: SPI1 must be on PA4–PA7, TIM2 can drive pins on PA0–PA3, TIM4 can drive PA8–PA11, etc. If you pick the wrong pins, CubeMX will reject or force conflicts.

**Steps:**

- [ ] **5.0.1** Open [real_time_controller.ioc](/home/musyani/Documents/Projects/card-issuance-system/firmware/real_time_controller/real_time_controller.ioc) in STM32CubeIDE (it opens in CubeMX by default). Check the "Pinout" view — note which pins are already assigned. _(0.5 hr)_

  > **Why:** See the current pinout so you don't accidentally override USART2 or the debug pins.

- [ ] **5.0.2** Sketch your pin assignment on paper (or a text file):
  - **SPI1 slave:** PA4 (CS), PA5 (CLK), PA6 (MOSI), PA7 (MISO)
  - **TIM2 stepper pulse:** PA0 (output on PWM channel 1 or GPIO, TIM2_CH1)
  - **TIM4 servo PWM:** PA8 (servo 0, TIM4_CH1), PA9 (servo 1, TIM4_CH2)
  - **Solenoid GPIO:** PA10 (output, any GPIO pin)
  - **Hall-effect sensor:** PA11 (GPIO input, pull-up)
  - **IR sensors:** PB0, PB1, PB2, PB5 (4× GPIO input, pull-up)
    _(0.5 hr)_

  > **Why:** These assignments avoid conflicts with USART2, debug, and the LED. The F401 has fixed SPI1 pins, so you _must_ use PA4–PA7 for SPI. TIM2 and TIM4 are flexible but the above choices work on this chip.

- [ ] **5.0.3** Cross-check against the Nucleo schematic (search online for "STM32 Nucleo-F401RE pinout PDF"). Confirm:
  - PA4–PA7 are free (not soldered to anything else on the board).
  - PA0–PA3, PA8–PA11, PB0, PB1, PB2, PB5 are available on the headers.
    _(0.5 hr)_

  > **Why:** The Nucleo has exposed header pins; you'll solder to these. Verify they exist before you commit to them in CubeMX.

- [ ] **5.0.4** Post your pin map in a comment or commit message so you have a record. Example:

  ```
  # STM32F401 Pin Assignment for Carousel Control
  SPI1_CS   = PA4   (slave chip select input)
  SPI1_CLK  = PA5   (slave clock input)
  SPI1_MOSI = PA6   (slave data in from Pi)
  SPI1_MISO = PA7   (slave data out to Pi)
  TIM2_CH1  = PA0   (stepper pulse output)
  TIM4_CH1  = PA8   (servo 0 latch PWM)
  TIM4_CH2  = PA9   (servo 1 ejector PWM)
  GPIO_OUT  = PA10  (solenoid lock control)
  GPIO_IN1  = PA11  (hall-effect sensor)
  GPIO_IN2  = PB0   (IR sensor 1 - door)
  GPIO_IN3  = PB1   (IR sensor 2 - rear gate)
  GPIO_IN4  = PB2   (IR sensor 3 - front gate)
  GPIO_IN5  = PB5   (IR sensor 4 - reject bin)
  ```

  _(0.25 hr)_

#### Subtotal: ~1.75 hrs

---

## Task 5.1 — CubeMX Peripheral Configuration and Code Generation

> _Enable SPI1, TIM2, TIM4, and the GPIO pins in the CubeMX configuration. Let CubeMX generate all the initialization code. Your job is to get the config right; CubeMX handles the boilerplate._

**Context:**
CubeMX is a visual tool that generates C code. You tell it "enable SPI1 in slave mode" and it writes the `HAL_SPI1_Init()` function, sets up clock dividers, and wires the interrupt vectors. This saves hours of manual register hacking.

**Steps:**

- [ ] **5.1.1** In STM32CubeIDE, open the `.ioc` file. It launches CubeMX. Click the **Pinout & Configuration** tab. _(0.25 hr)_

- [ ] **5.1.2** In the left panel, under **Connectivity**, right-click and select **Add Peripheral** → **SPI**. Choose **SPI1**. _(0.25 hr)_

  > **What happens:** CubeMX auto-assigns SPI1 to PA4–PA7 (the only SPI1 option on this chip). It shows a green checkmark if there are no conflicts.

- [ ] **5.1.3** In the SPI1 panel that appears on the right, set:
  - **Mode:** Slave (not Master)
  - **Hardware NSS Signal:** Use NSS Output (CS from Pi)
  - **Baud Rate:** 1 MHz
  - Keep all other settings default.
    _(0.5 hr)_

- [ ] **5.1.4** Add **TIM2**: Right-click → **Add Peripheral** → **Timer** → **TIM2**. Set:
  - **Clock Source:** Internal Clock
  - **Channel 1:** PWM Generation (for stepper pulse)
  - **Prescaler:** 83 (gives 1 MHz tick from 84 MHz clock)
  - **Auto Reload:** 99 (gives 10 kHz PWM output)
    _(0.5 hr)_

  > **Why these values?** At 1 MHz tick, counting 0–99 gives 10 kHz, which is a reasonable stepper pulse rate. You can tune later.

- [ ] **5.1.5** Add **TIM4**: Right-click → **Add Peripheral** → **Timer** → **TIM4**. Set:
  - **Clock Source:** Internal Clock
  - **Channel 1 & 2:** PWM Generation
  - **Prescaler:** 839 (gives 100 kHz tick from 84 MHz clock)
  - **Auto Reload:** 1999 (gives 50 Hz PWM = 20 ms period, correct for servo)
    _(0.5 hr)_

  > **Why?** Servos need exactly 50 Hz (20 ms period). At 100 kHz tick, 0–1999 counts = 20 ms.

- [ ] **5.1.6** In the left panel, click **GPIO** and configure the sensor/solenoid pins:
  - PA10 (solenoid): **Output, GPIO_Output**, label "SOLENOID_LOCK"
  - PA11, PB0, PB1, PB2, PB5 (sensors): **Input, GPIO_Input**, pull-up mode, labels "HALL*SENSOR", "IR_DOOR", "IR_REAR_GATE", "IR_FRONT_GATE", "IR_REJECT"
    *(1 hr)\_

- [ ] **5.1.7** Click **Project** → **Generate Code**. CubeMX creates all the peripheral init functions and wires the interrupt vectors. _(0.5 hr)_

- [ ] **5.1.8** In STM32CubeIDE, right-click the project → **Refresh** to reload the generated files. _(0.25 hr)_

#### Subtotal: ~3.5 hrs

---

## Task 5.2 — Build and Verify the Generated Skeleton Code

> _Confirm that the CubeMX-generated code compiles and runs on the Nucleo without any custom logic yet. This proves the peripheral config is sound and the toolchain works._

**Context:**
You haven't written any firmware logic yet. CubeMX just generated init functions and left `main()` with a while(1) loop. Your goal: compile, flash, and confirm the board is alive.

**Steps:**

- [ ] **5.2.1** In STM32CubeIDE, open [Src/main.c](/home/musyani/Documents/Projects/card-issuance-system/firmware/real_time_controller/Src/main.c). Find the `main()` function. Confirm it calls `MX_SPI1_Init()`, `MX_TIM2_Init()`, `MX_TIM4_Init()`, and `MX_GPIO_Init()`. _(0.25 hr)_

- [ ] **5.2.2** Press **Ctrl+B** to build the project. _(0.5 hr)_

  > **Expected result:** Build succeeds with no errors, possibly a few warnings (which are fine).
  > **If it fails:** You have a pin conflict or a CubeMX setting error. Check the error log and adjust the config in step 5.1.

- [ ] **5.2.3** Plug the Nucleo into your laptop via USB. A new serial port (e.g. `/dev/ttyACM0` on Linux) appears. _(0.5 hr)_

- [ ] **5.2.4** In STM32CubeIDE, press **Ctrl+F11** to launch the debugger. (Or: "Run" → "Debug As" → "Embedded C/C++ Application".) _(0.5 hr)_

  > **What happens:** The IDE compiles again, flashes the binary to the Nucleo via USB ST-Link, and pauses at `main()`.

- [ ] **5.2.5** Press **F8** (or the Resume button) to let the code run. _(0.25 hr)_

  > **Expected behavior:** The board runs the init functions and enters the while(1) loop. Nothing visible happens yet (the LED should still blink if you have that code), but there are no crashes.

- [ ] **5.2.6** Open a serial terminal (e.g. `picocom /dev/ttyACM0 -b 115200` on Linux) and confirm you see no error messages on UART2. _(0.5 hr)_

  > **Why?** If the init functions failed, the code might print error messages. Silence is good here.

#### Subtotal: ~3 hrs

---

## Task 5.3 — SPI Frame Parser and Command Router

> _Implement the SPI frame reception, checksum validation, and command dispatch. This is the "hello world" between the Pi and STM32—if SPI doesn't work, nothing else matters._

**Context:**
When the Pi sends a 3-byte SPI frame (e.g., `[0x10, 0x05, 0x15]` = rotate to slot 5), the STM32 must:

1. Receive all 3 bytes via SPI interrupt.
2. Validate the checksum (XOR of first two bytes).
3. Route to the correct command handler.
4. Send back a 3-byte response.

**Steps:**

- [ ] **5.3.1** In [Src/main.c](/home/musyani/Documents/Projects/card-issuance-system/firmware/real_time_controller/Src/main.c), add global buffers and state machine in the **USER CODE BEGIN 1** section:

  ```c
  /* USER CODE BEGIN 1 */
  #define SPI_FRAME_SIZE 3
  uint8_t spi_rx_buffer[SPI_FRAME_SIZE] = {0};
  uint8_t spi_tx_buffer[SPI_FRAME_SIZE] = {0};
  uint8_t spi_byte_count = 0;

  // Command and response codes (from SPI_PROTOCOL.md)
  #define CMD_ROTATE_TO_SLOT 0x10
  #define CMD_GET_SENSOR_STATE 0x40
  #define RESP_ACK 0x00
  #define RESP_ERROR 0x04
  /* USER CODE END 1 */
  ```

  _(0.5 hr)_

- [ ] **5.3.2** In [Src/stm32f4xx_it.c](/home/musyani/Documents/Projects/card-issuance-system/firmware/real_time_controller/Src/stm32f4xx_it.c), find the `SPI1_IRQHandler()` function (CubeMX created a stub). Replace it with a frame receiver:

  ```c
  void SPI1_IRQHandler(void)
  {
      HAL_SPI_IRQHandler(&hspi1);
  }

  void HAL_SPI_RxCpltCallback(SPI_HandleTypeDef *hspi)
  {
      if (hspi->Instance == SPI1) {
          // A byte arrived
          spi_rx_buffer[spi_byte_count++] = hspi->pRxBuffPtr[0];

          if (spi_byte_count == SPI_FRAME_SIZE) {
              // Full frame received: validate checksum
              uint8_t cmd = spi_rx_buffer[0];
              uint8_t param = spi_rx_buffer[1];
              uint8_t checksum_rx = spi_rx_buffer[2];
              uint8_t checksum_calc = cmd ^ param;

              if (checksum_rx == checksum_calc) {
                  // Valid frame: route the command
                  route_command(cmd, param);
              } else {
                  // Bad checksum
                  spi_tx_buffer[0] = RESP_ERROR;
                  spi_tx_buffer[1] = 0x00;
                  spi_tx_buffer[2] = 0x04;
              }

              // Reset for next frame
              spi_byte_count = 0;
              HAL_SPI_TransmitReceive_IT(&hspi1, spi_tx_buffer, spi_rx_buffer, SPI_FRAME_SIZE);
          }
      }
  }
  ```

  _(1.5 hrs)_

  > **This is the SPI backbone.** Every command goes through this. Get it right, and everything else flows. Get it wrong, and the Pi can't talk to the STM32.

- [ ] **5.3.3** In [Src/main.c](/home/musyani/Documents/Projects/card-issuance-system/firmware/real_time_controller/Src/main.c), add a command router function in **USER CODE BEGIN 4** section:

  ```c
  void route_command(uint8_t cmd, uint8_t param)
  {
      switch (cmd) {
          case CMD_ROTATE_TO_SLOT:
              spi_tx_buffer[0] = RESP_ACK;
              spi_tx_buffer[1] = 0x00;
              break;
          case CMD_GET_SENSOR_STATE:
              spi_tx_buffer[0] = RESP_ACK;
              spi_tx_buffer[1] = 0x00;  // Placeholder: read sensors later
              break;
          default:
              spi_tx_buffer[0] = RESP_ERROR;
              spi_tx_buffer[1] = 0x00;
              break;
      }
      spi_tx_buffer[2] = spi_tx_buffer[0] ^ spi_tx_buffer[1];  // Checksum
  }
  ```

  _(0.5 hr)_

- [ ] **5.3.4** Start SPI communication in `main()` after all inits. In **USER CODE BEGIN 2** (after all `MX_*_Init()` calls):

  ```c
  HAL_SPI_TransmitReceive_IT(&hspi1, spi_tx_buffer, spi_rx_buffer, SPI_FRAME_SIZE);
  ```

  _(0.25 hr)_

- [ ] **5.3.5** Build and flash the firmware again. _(0.5 hr)_

#### Subtotal: ~3.25 hrs

---

## Task 5.4 — SPI Loopback Test with the Pi

> _Run the first end-to-end test: the Pi sends a command over SPI, the STM32 receives it, validates the checksum, and sends back an ACK. No motors yet—just the bus._

**Context:**
You now have firmware that can receive SPI frames. The Pi already has `spi_master.py` written (Phase 4, Task 4.5). Time to prove they can talk.

**Steps:**

- [ ] **5.4.1** On the Pi, verify that SPI is enabled. SSH into the Pi and run:

  ```bash
  ls /dev/spidev*
  ```

  You should see `/dev/spidev0.0`. If not, enable SPI via `raspi-config`. _(0.5 hr)_

- [ ] **5.4.2** Wire the Pi to the Nucleo over SPI. Connect:
  - Pi GPIO 10 (MOSI) → Nucleo PA6 (MOSI)
  - Pi GPIO 9 (MISO) → Nucleo PA7 (MISO)
  - Pi GPIO 11 (CLK) → Nucleo PA5 (CLK)
  - Pi GPIO 8 (CS) → Nucleo PA4 (CS)
  - Pi GND → Nucleo GND (important!)
    _(0.5 hr)_

  > **Use a ribbon cable or breadboard jumpers.** SPI is sensitive to noise; keep wires short (~30 cm max) and ensure the ground connection is solid.

- [ ] **5.4.3** On the Pi, test the SPI bus with a simple Python script:

  ```python
  import spidev

  spi = spidev.SpiDev(0, 0)
  spi.max_speed_hz = 1000000  # 1 MHz
  spi.mode = 0

  # Send: ROTATE_TO_SLOT(5) = [0x10, 0x05, 0x15]
  cmd = [0x10, 0x05, 0x15]
  response = spi.xfer2(cmd)
  print(f"Sent: {[hex(b) for b in cmd]}")
  print(f"Received: {[hex(b) for b in response]}")

  spi.close()
  ```

  _(1 hr)_

  > **Expected output:** The response should be `['0xc', '0x0', '0xc']` or similar (the exact values depend on SPI timing, but you should see _something_). If you see all zeros or garbage, check:
  >
  > - The wiring (especially CS and GND)
  > - The STM32 is running (check with debugger)
  > - The SPI interrupt is enabled (check in CubeMX, you may need to enable SPI1 interrupt in NVIC)

- [ ] **5.4.4** If you got a valid response, document the test result. If not, debug:
  - Check that `SPI1_IRQHandler` is being called (set a breakpoint in the debugger).
  - Check that the frame parser is receiving bytes.
  - Review the CubeMX SPI1 config (mode should be Slave, NSS should be enabled).
    _(1 hr)_

- [ ] **5.4.5** Once the SPI loopback works, commit this milestone. You've proven the bus. _(0.25 hr)_

#### Subtotal: ~3.75 hrs

---

## Task 5.5 — Stepper Motor Pulse Generation and Timing

> _Implement TIM2 interrupt-driven stepper pulse generation. The goal: send a fixed pulse train at a configurable frequency without blocking the SPI handler. Test on the bench with a NEMA 17 motor before adding the carousel._

**Context:**
The stepper motor needs precise, regular pulses. You'll use TIM2's interrupt to generate these pulses at a fixed rate. The Pi will send `ROTATE_TO_SLOT(index)`, and the STM32 will pulse the motor until it reaches the target position.

**Steps:**

- [ ] **5.5.1** In [Src/main.c](/home/musyani/Documents/Projects/card-issuance-system/firmware/real_time_controller/Src/main.c), add stepper state variables in **USER CODE BEGIN 1**:

  ```c
  #define STEPS_PER_SLOT 20  // Adjust based on motor + gearing
  #define STEPPER_PULSE_PIN GPIO_PIN_0
  #define STEPPER_PULSE_PORT GPIOA

  int32_t current_step = 0;
  int32_t target_step = 0;
  uint8_t stepper_active = 0;
  ```

  _(0.5 hr)_

- [ ] **5.5.2** In [Src/stm32f4xx_it.c](/home/musyani/Documents/Projects/card-issuance-system/firmware/real_time_controller/Src/stm32f4xx_it.c), implement `TIM2_IRQHandler()`:

  ```c
  void TIM2_IRQHandler(void)
  {
      HAL_TIM_IRQHandler(&htim2);
  }

  void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim)
  {
      if (htim->Instance == TIM2) {
          if (stepper_active && current_step < target_step) {
              // Toggle pulse pin (pulse = 1 clock tick = 1 step)
              HAL_GPIO_TogglePin(STEPPER_PULSE_PORT, STEPPER_PULSE_PIN);
              current_step++;
          } else if (current_step >= target_step) {
              stepper_active = 0;
              HAL_TIM_Base_Stop_IT(&htim2);  // Stop timer
          }
      }
  }
  ```

  _(1 hr)_

- [ ] **5.5.3** Add a `rotate_to_slot(index)` function in **USER CODE BEGIN 4**:

  ```c
  void rotate_to_slot(uint8_t slot_index)
  {
      if (slot_index > 9) {
          spi_tx_buffer[0] = RESP_ERROR;
          spi_tx_buffer[1] = 0x00;
          return;
      }

      target_step = slot_index * STEPS_PER_SLOT;
      stepper_active = 1;
      current_step = 0;

      HAL_TIM_Base_Start_IT(&htim2);  // Start generating pulses

      spi_tx_buffer[0] = RESP_ACK;
      spi_tx_buffer[1] = 0x00;
  }
  ```

  _(0.75 hr)_

- [ ] **5.5.4** Update the command router to call `rotate_to_slot()`:

  ```c
  case CMD_ROTATE_TO_SLOT:
      rotate_to_slot(param);
      break;
  ```

  _(0.25 hr)_

- [ ] **5.5.5** Wire a NEMA 17 stepper motor to the STM32:
  - PA0 (pulse) → A4988 STEP pin
  - Any GND → A4988 GND
  - The A4988 driver handles the rest (DIR, ENABLE, power).
  - Connect 12V power to the A4988 (or a USB power bank with sufficient current).
    _(0.5 hr)_

- [ ] **5.5.6** Build, flash, and test:

  ```python
  # On Pi
  spi = spidev.SpiDev(0, 0)
  spi.max_speed_hz = 1000000
  spi.mode = 0

  # Rotate to slot 3 = 20 * 3 = 60 steps
  cmd = [0x10, 0x03, 0x13]  # ROTATE_TO_SLOT(3)
  response = spi.xfer2(cmd)

  time.sleep(0.5)  # Wait for motor to finish

  # Query sensor state to see if motor is done
  cmd = [0x40, 0x00, 0x40]  # GET_SENSOR_STATE
  response = spi.xfer2(cmd)
  ```

  Listen to the stepper motor or watch it with an oscilloscope. You should hear it step or see a pulse train at PA0. _(1 hr)_

- [ ] **5.5.7** If the motor steps correctly, calibrate `STEPS_PER_SLOT`. Measure the actual physical rotation and adjust the constant so slot 0 → slot 1 is exactly 36° (360° / 10 slots). _(1 hr)_

#### Subtotal: ~5 hrs

---

## Task 5.6 — Hall-Effect Home Sensor and Carousel Referencing

> _Implement `HOME_CAROUSEL()` to rotate the carousel until the A3144 hall-effect sensor triggers. This locks in the mechanical home position so slot 0 is always repeatable._

**Context:**
Steppers lose sync if you stall or overload them. The hall sensor is your "zero"—rotate until it triggers, then you know exactly where you are. Every power-up, call `HOME_CAROUSEL()` first.

**Steps:**

- [ ] **5.6.1** In [Src/main.c](/home/musyani/Documents/Projects/card-issuance-system/firmware/real_time_controller/Src/main.c), add a `home_carousel()` function in **USER CODE BEGIN 4**:

  ```c
  void home_carousel(void)
  {
      current_step = 0;
      target_step = 9999;  // Rotate until sensor triggers
      stepper_active = 1;

      HAL_TIM_Base_Start_IT(&htim2);

      // Wait for sensor (blocking, 5 second timeout)
      uint32_t start_time = HAL_GetTick();
      while (stepper_active && (HAL_GetTick() - start_time) < 5000) {
          if (!HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_11)) {  // Hall sensor low = magnet present
              current_step = 0;  // Reset step counter
              stepper_active = 0;
              HAL_TIM_Base_Stop_IT(&htim2);
              break;
          }
      }

      spi_tx_buffer[0] = stepper_active ? RESP_ERROR : RESP_ACK;
      spi_tx_buffer[1] = 0x00;
  }
  ```

  _(1 hr)_

- [ ] **5.6.2** Add a command handler for `CMD_HOME_CAROUSEL` (0x41 in SPI_PROTOCOL.md):

  ```c
  #define CMD_HOME_CAROUSEL 0x41

  case CMD_HOME_CAROUSEL:
      home_carousel();
      break;
  ```

  _(0.25 hr)_

- [ ] **5.6.3** Wire the A3144 hall-effect sensor:
  - VCC (red) → 3.3V on Nucleo
  - GND (black) → GND
  - OUT (green) → PA11 (GPIO input, pull-up)
    Mount the sensor on the carousel frame and attach a neodymium magnet to the disc rim at the slot-0 position.
    _(0.5 hr)_

- [ ] **5.6.4** Test on the bench:

  ```python
  # On Pi: home the carousel
  cmd = [0x41, 0x00, 0x41]  # HOME_CAROUSEL
  response = spi.xfer2(cmd)
  print(f"Home response: {[hex(b) for b in response]}")
  ```

  The motor should spin until the magnet passes the sensor, then stop. _(1 hr)_

- [ ] **5.6.5** Verify: rotate to slots 0, 1, 5, 9 using `ROTATE_TO_SLOT`, and measure the physical positions. They should be evenly spaced at 36° intervals. If not, adjust `STEPS_PER_SLOT` again. _(0.5 hr)_

#### Subtotal: ~3.25 hrs

---

## Task 5.7 — Servo PWM Control (Latch and Ejector)

> _Configure TIM4 to output 50 Hz PWM on PA8 and PA9 for two SG90 servos. Implement `set_servo_angle()` to map 0–180° to 1–2 ms pulse widths._

**Context:**
SG90 servos are standard hobby servos. A 1 ms pulse = 0°, 1.5 ms = 90°, 2 ms = 180°. At 50 Hz (20 ms period), you count up to 2000 and vary where the pulse goes high. Simple math, but TIM4 needs the right prescaler.

**Steps:**

- [ ] **5.7.1** In [Src/main.c](/home/musyani/Documents/Projects/card-issuance-system/firmware/real_time_controller/Src/main.c), add servo control functions in **USER CODE BEGIN 4**:

  ```c
  #define SERVO0_CHANNEL TIM_CHANNEL_1  // PA8
  #define SERVO1_CHANNEL TIM_CHANNEL_2  // PA9
  #define SERVO_MIN_US 1000   // 1 ms = 0°
  #define SERVO_MAX_US 2000   // 2 ms = 180°
  #define SERVO_PERIOD 20000  // 20 ms total period

  void set_servo_angle(uint8_t servo_id, uint8_t angle)
  {
      // angle: 0–180
      uint32_t pulse_us = SERVO_MIN_US + (angle * (SERVO_MAX_US - SERVO_MIN_US)) / 180;
      uint32_t compare_value = pulse_us;  // Already in timer ticks (prescaler makes it 1 us = 1 tick)

      if (servo_id == 0) {
          __HAL_TIM_SetCompare(&htim4, SERVO0_CHANNEL, compare_value);
      } else if (servo_id == 1) {
          __HAL_TIM_SetCompare(&htim4, SERVO1_CHANNEL, compare_value);
      }
  }
  ```

  _(0.75 hr)_

- [ ] **5.7.2** In the command router, add handlers for servo commands:

  ```c
  #define CMD_LATCH_CARD 0x12
  #define CMD_RELEASE_LATCH 0x13

  case CMD_LATCH_CARD:
      set_servo_angle(0, 180);  // Servo 0 (latch) fully engaged
      spi_tx_buffer[0] = RESP_ACK;
      spi_tx_buffer[1] = 0x00;
      break;
  case CMD_RELEASE_LATCH:
      set_servo_angle(0, 0);    // Servo 0 (latch) retracted
      spi_tx_buffer[0] = RESP_ACK;
      spi_tx_buffer[1] = 0x00;
      break;
  ```

  _(0.5 hr)_

- [ ] **5.7.3** Start TIM4 PWM at the top of the main loop (in **USER CODE BEGIN 2** after init):

  ```c
  HAL_TIM_PWM_Start(&htim4, SERVO0_CHANNEL);
  HAL_TIM_PWM_Start(&htim4, SERVO1_CHANNEL);
  set_servo_angle(0, 90);  // Set servo 0 to neutral (90°)
  set_servo_angle(1, 90);  // Set servo 1 to neutral (90°)
  ```

  _(0.25 hr)_

- [ ] **5.7.4** Wire the servos:
  - Servo 0 (latch) signal → PA8
  - Servo 1 (ejector) signal → PA9
  - Both servos: VCC (red) → 5V (use a separate power supply, not the Nucleo USB), GND (black) → GND (shared with Nucleo)
    _(0.5 hr)_

- [ ] **5.7.5** Test on the bench:

  ```python
  # On Pi: latch the card
  cmd = [0x12, 0x00, 0x12]  # LATCH_CARD
  response = spi.xfer2(cmd)

  time.sleep(0.5)

  # Release latch
  cmd = [0x13, 0x00, 0x13]  # RELEASE_LATCH
  response = spi.xfer2(cmd)
  ```

  Watch the servos sweep. Servo 0 should move to hold position, then release. _(1 hr)_

#### Subtotal: ~3.5 hrs

---

## Task 5.8 — Solenoid Lock and IR Sensor Input

> _Add GPIO output for the solenoid door lock and GPIO inputs for the 4 IR break-beam sensors. Implement `lock_door()`, `unlock_door()`, and `GET_SENSOR_STATE` to pack all 5 sensor readings into a single response byte._

**Context:**
The solenoid is a simple GPIO output (high = locked, low = unlocked). The IR sensors are GPIO inputs (pull-up, low = beam broken). You'll read all 5 sensors and pack them into one response byte following the SPI_PROTOCOL.md spec.

**Steps:**

- [ ] **5.8.1** In [Src/main.c](/home/musyani/Documents/Projects/card-issuance-system/firmware/real_time_controller/Src/main.c), add solenoid and sensor control functions in **USER CODE BEGIN 4**:

  ```c
  #define SOLENOID_LOCK_PIN GPIO_PIN_10
  #define SOLENOID_LOCK_PORT GPIOA
  #define HALL_SENSOR_PIN GPIO_PIN_11
  #define IR_DOOR_PIN GPIO_PIN_0
  #define IR_REAR_GATE_PIN GPIO_PIN_1
  #define IR_FRONT_GATE_PIN GPIO_PIN_2
  #define IR_REJECT_PIN GPIO_PIN_5

  void lock_door(void)
  {
      HAL_GPIO_WritePin(SOLENOID_LOCK_PORT, SOLENOID_LOCK_PIN, GPIO_PIN_SET);
      spi_tx_buffer[0] = RESP_ACK;
      spi_tx_buffer[1] = 0x00;
  }

  void unlock_door(void)
  {
      HAL_GPIO_WritePin(SOLENOID_LOCK_PORT, SOLENOID_LOCK_PIN, GPIO_PIN_RESET);
      spi_tx_buffer[0] = RESP_ACK;
      spi_tx_buffer[1] = 0x00;
  }

  uint8_t get_sensor_state(void)
  {
      // Pack sensor bits (see SPI_PROTOCOL.md)
      uint8_t state = 0;

      if (!HAL_GPIO_ReadPin(GPIOA, HALL_SENSOR_PIN)) {
          state |= 0x80;  // Bit 7: Hall sensor triggered
      }
      if (!HAL_GPIO_ReadPin(GPIOB, IR_DOOR_PIN)) {
          state |= 0x40;  // Bit 6: Door open
      }
      if (!HAL_GPIO_ReadPin(GPIOB, IR_REAR_GATE_PIN)) {
          state |= 0x20;  // Bit 5: Card at rear gate
      }
      if (!HAL_GPIO_ReadPin(GPIOB, IR_FRONT_GATE_PIN)) {
          state |= 0x10;  // Bit 4: Card at front gate
      }
      if (!HAL_GPIO_ReadPin(GPIOB, IR_REJECT_PIN)) {
          state |= 0x08;  // Bit 3: Card in reject bin
      }

      spi_tx_buffer[0] = 0x03;  // SENSOR_STATE_PAYLOAD response code
      spi_tx_buffer[1] = state;

      return state;
  }
  ```

  _(1 hr)_

- [ ] **5.8.2** Add command handlers:

  ```c
  #define CMD_LOCK_DOOR 0x20
  #define CMD_UNLOCK_DOOR 0x21
  #define CMD_GET_SENSOR_STATE 0x40

  case CMD_LOCK_DOOR:
      lock_door();
      break;
  case CMD_UNLOCK_DOOR:
      unlock_door();
      break;
  case CMD_GET_SENSOR_STATE:
      get_sensor_state();
      break;
  ```

  _(0.5 hr)_

- [ ] **5.8.3** Wire the solenoid lock and IR sensors:
  - Solenoid control → PA10 (through a MOSFET driver for power isolation)
  - Hall-effect sensor → PA11 (already done in Task 5.6)
  - IR sensor 1 (door) → PB0
  - IR sensor 2 (rear gate) → PB1
  - IR sensor 3 (front gate) → PB2
  - IR sensor 4 (reject bin) → PB5
    All sensors pull-up, logic inverted (low = beam broken).
    _(1 hr)_

- [ ] **5.8.4** Test on the bench:

  ```python
  # On Pi: lock door
  cmd = [0x20, 0x00, 0x20]  # LOCK_DOOR
  response = spi.xfer2(cmd)

  time.sleep(0.25)

  # Get sensor state
  cmd = [0x40, 0x00, 0x40]  # GET_SENSOR_STATE
  response = spi.xfer2(cmd)
  print(f"Sensor state: {bin(response[1])}")

  # Unlock door
  cmd = [0x21, 0x00, 0x21]  # UNLOCK_DOOR
  response = spi.xfer2(cmd)
  ```

  Listen for the solenoid click. Break IR beams and watch the sensor byte change. _(1 hr)_

#### Subtotal: ~3.5 hrs

---

## Task 5.9 — Turntable and Frame Fabrication

> _Now that the firmware is proven, build the physical carousel. Cut the acrylic turntable, assemble the frame, mount the motor and sensors. Mechanical precision is critical; a well-built carousel makes integration painless._

**Context:**
Firmware is done. The STM32 responds to every command. Now you build the hardware to match. This is not a coding task, but it must be done before mechanical testing.

**Steps:**

- [ ] **5.9.1** Design and cut the 10-slot turntable disc from 5mm acrylic:
  - 10 radial pockets (each CR80-sized: 85.6 × 53.98 mm) arranged at 36° intervals around a center hub.
  - Center hub: 8 mm hole (for the drive shaft).
  - Use a CAD tool (e.g., FreeCAD, Fusion 360) to design, then send to a laser cutter or use a CNC router.
    _(2 hrs)_

- [ ] **5.9.2** Fabricate the carousel frame (base plate, motor mount, bearing support, timing belt path):
  - Base plate: 10 × 10 inch acrylic or aluminum, 5 mm thick.
  - NEMA 17 motor mount on the base, with pulley on the motor shaft.
  - Bearing support: pillow bearing at the disc center, mounted on a standoff above the base.
  - Timing belt path: 2 × timing belt pulleys (one on motor shaft, one on disc shaft) with a 1:1 ratio.
    _(2 hrs)_

- [ ] **5.9.3** Install timing belt and pulley coupling:
  - Run a timing belt between motor pulley and disc pulley.
  - Verify belt tension (thumbs-down, should deflect ~1 cm at midpoint).
  - Test rotation by hand: disc should spin smoothly with no grinding.
    _(1 hr)_

- [ ] **5.9.4** Mount A3144 hall-effect sensor on frame and attach magnet to disc rim:
  - Attach sensor on a bracket near the disc rim, 2 mm away, pointing inward.
  - Glue a small neodymium magnet to the disc rim at the slot-0 reference position.
  - Test: rotate disc by hand and confirm sensor triggers (continuity meter shows low) once per revolution.
    _(0.5 hr)_

- [ ] **5.9.5** Mount all 4 IR break-beam sensor pairs:
  - Door frame: one transmitter/receiver pair, ~30 cm apart, spanning the rear door opening.
  - Rear gate: pair at the carousel entry, perpendicular to card flow.
  - Front gate: pair at the ejection slot, perpendicular to card flow.
  - Reject bin: pair inside the reject bin, catching diverted cards.
    Use adjustable brackets so you can tune alignment later.
    _(1 hr)_

- [ ] **5.9.6** Install neodymium retention magnets in each of the 10 carousel slots:
  - Glue a small magnet (e.g., 6 × 3 mm) in the center of each CR80 pocket.
  - Test: place a card in each slot and confirm it holds during gentle rotation without magnet hold-down.
    _(0.5 hr)_

#### Subtotal: ~7.5 hrs

---

## Task 5.10 — Conveyor 1 and Expired Card Slot Assembly

> _Build the input conveyor (staff loading path) and the expired card scan station (returning student path). These are simpler than the carousel, so they come last._

**Context:**
Two independent subsystems: Conveyor 1 feeds cards to the carousel, and the expired card slot scans returning students' old cards. Both have their own motor or servo control but don't affect carousel validation.

**Steps:**

- [ ] **5.10.1** Assemble Conveyor 1 belt kit:
  - Two aluminum rollers, 30 cm wide, 10 cm diameter.
  - Timing belt wrapped around rollers, mounted on a frame inclined at ~5° toward the carousel.
  - NEMA 17 motor drives one roller (motor shaft pulley → roller pulley, 1:1).
  - Feed tray on the input end, carousel rear gate sensor on the output end.
    _(1.5 hrs)_

- [ ] **5.10.2** Mount second NEMA 17 motor and drive roller coupling for Conveyor 1:
  - Attach motor to the frame bracket.
  - Connect motor shaft pulley to roller drive pulley via timing belt.
  - Test: run belt by hand, verify smooth operation and no slippage.
    _(0.5 hr)_

- [ ] **5.10.3** Test card transport end-to-end:
  - Place a CR80 card in the feed tray.
  - Command the Pi to run the conveyor (send `FEED_CARD` SPI command to STM32).
  - Verify the card arrives at the rear gate sensor (IR beam breaks).
  - If card jams, adjust the belt tension or the incline angle.
    _(0.5 hr)_

- [ ] **5.10.4** Fabricate expired card scan slot assembly:
  - A slide channel sized for CR80 card width, mounted next to the carousel.
  - Latch servo mounted above the channel, controlled by `LATCH_CARD` / `RELEASE_LATCH` commands.
  - USB camera mounted below the slot to capture the card image for OCR.
  - Ejection into the "returning student collection bin" on release.
    _(1 hr)_

- [ ] **5.10.5** Test latch servo and card handling:
  - Place a card in the slot.
  - Send `LATCH_CARD` command — the servo should hold the card firmly.
  - Send `RELEASE_LATCH` command — the servo should release the card into the bin.
  - Repeat 10 times to verify consistent operation.
    _(0.5 hr)_

#### Subtotal: ~4 hrs

---

#### Phase 5 Total Estimated Time: ~41.5 hrs

---

## Summary

| Task      | Subtotal      | What You're Proving                   |
| --------- | ------------- | ------------------------------------- |
| 5.0       | 1.75 hrs      | Hardware design (pins committed)      |
| 5.1       | 3.5 hrs       | CubeMX config is solid                |
| 5.2       | 3 hrs         | Toolchain works (build, flash, debug) |
| 5.3       | 3.25 hrs      | SPI frame parser ready                |
| 5.4       | 3.75 hrs      | Pi ↔ STM32 bus is alive               |
| 5.5       | 5 hrs         | Stepper motor responds to commands    |
| 5.6       | 3.25 hrs      | Hall sensor homes carousel reliably   |
| 5.7       | 3.5 hrs       | Servo PWM controls actuators          |
| 5.8       | 3.5 hrs       | All sensors read, solenoid toggles    |
| 5.9       | 7.5 hrs       | Mechanical carousel built & aligned   |
| 5.10      | 4 hrs         | Conveyor and card slot working        |
| **TOTAL** | **~41.5 hrs** | **Full hardware stack operational**   |
