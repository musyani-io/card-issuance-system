#include <Arduino.h>
#include <Servo.h>
#include <SPI.h>
#include <string.h>

// Objects
Servo servo1; // card holder (60 DOWN, FLIPS THE CARD, 2 SECONDS HOLD)
Servo servo2; // carousel rotater
Servo servo3;

// Pin definition
#define SERVO1 22
#define SERVO2 23
#define SERVO3 24

// Hardware SPI pins on the Mega 2560
constexpr uint8_t SPI_SS_PIN = 53;
constexpr uint8_t SPI_MOSI_PIN = 51;
constexpr uint8_t SPI_MISO_PIN = 50;
constexpr uint8_t SPI_SCK_PIN = 52;

// SPI status frames from Raspberry Pi: "00" for error, "1X" for success
constexpr uint8_t SPI_FRAME_LEN = 2;

volatile char spiFrame[SPI_FRAME_LEN + 1] = {0};
volatile uint8_t spiFrameIndex = 0;
volatile bool spiFrameReady = false;

// Constants
constexpr int ORIGIN_PULSE = 544;  // Standard 0-degree microsecond mapping
constexpr int MAX_PULSE = 2400;    // Standard 180-degree microsecond mapping
constexpr int CARD_DOWN = 60;

// Functions
void setupSpiReceiver();
bool receiveSpiMessage(char *out, size_t outSize);
void servoToOrigin(Servo &servo);
void servoToAngle(Servo &servo, int angle);

ISR(SPI_STC_vect) {
  char received = static_cast<char>(SPDR);

  if (spiFrameIndex < SPI_FRAME_LEN) {
    spiFrame[spiFrameIndex++] = received;
    if (spiFrameIndex == SPI_FRAME_LEN) {
      spiFrame[SPI_FRAME_LEN] = '\0';
      spiFrameReady = true;
      spiFrameIndex = 0;
    }
  } else {
    spiFrameIndex = 0;
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("System initializing!");
  delayMicroseconds(10);

  setupSpiReceiver();

  // 1. Pre-load the 0-degree pulse width BEFORE attaching the pins
  servo1.writeMicroseconds(ORIGIN_PULSE);
  servo2.writeMicroseconds(ORIGIN_PULSE);
  servo3.writeMicroseconds(ORIGIN_PULSE);
  delayMicroseconds(10);

  // 2. Attach motors (they will now initialize quietly at 544 µs instead of jumping)
  servo1.attach(SERVO1);
  servo2.attach(SERVO2);
  servo3.attach(SERVO3);
  delayMicroseconds(100);

  // 3. Verify homing alignment softly
  Serial.println("Homing verification...");
  servoToOrigin(servo1);
  servoToOrigin(servo2);
  servoToOrigin(servo3);

  Serial.println("System Ready! Awaiting SPI commands...");
}

void loop() {
  // Clear software buffer memory tracking whenever the Pi releases Chip Select (SS Pin goes HIGH)
  if (digitalRead(SPI_SS_PIN) == HIGH) {
    spiFrameIndex = 0;
  }
  
  char spiMessage[SPI_FRAME_LEN + 1];

  // Evaluate message logic if a frame is fully assembled
  if (receiveSpiMessage(spiMessage, sizeof(spiMessage))) {
    
    if (strcmp(spiMessage, "10") == 0) {
      Serial.println("Target: Compartment A -> Entrance (0 deg)");
      servoToAngle(servo2, 0);
      delay(2000);
      servoToAngle(servo1, 70);
      delay(1000);
      servoToOrigin(servo1);
      servoToOrigin(servo2);
    } 
    else if (strcmp(spiMessage, "00") == 0) {
      Serial.println("Target: Compartment C -> Entrance (90 deg)");
      servoToAngle(servo2, 90);
      delay(2000);
      servoToAngle(servo1, 70);
      delay(1000);
      servoToOrigin(servo1);
      servoToOrigin(servo2);
    } 
    else if (strcmp(spiMessage, "11") == 0) {
      Serial.println("Target: Compartment B -> Entrance (180 deg)");
      servoToAngle(servo2, 180);
      delay(2000);
      servoToAngle(servo1, 70);
      delay(1000);
      servoToOrigin(servo1);
      servoToOrigin(servo2);
    }
    else {
      Serial.print("Unknown Frame: ");
      Serial.println(spiMessage);
    }
  }
}

// SPI INFRASTRUCTURE FUNCTIONS

void setupSpiReceiver() {
  pinMode(SPI_SS_PIN, INPUT_PULLUP);
  pinMode(SPI_MOSI_PIN, INPUT);
  pinMode(SPI_SCK_PIN, INPUT);
  pinMode(SPI_MISO_PIN, OUTPUT);

  SPCR |= _BV(SPE);
  SPI.attachInterrupt();
}

bool readSpiFrame(char *out, size_t outSize) {
  if (out == nullptr || outSize < (SPI_FRAME_LEN + 1)) {
    return false;
  }

  noInterrupts();
  bool ready = spiFrameReady;
  if (ready) {
    out[0] = spiFrame[0];
    out[1] = spiFrame[1];
    out[2] = '\0';
    spiFrameReady = false;
  }
  interrupts();

  return ready;
}

bool receiveSpiMessage(char *out, size_t outSize) {
  if (!readSpiFrame(out, outSize)) {
    return false;
  }

  Serial.print("Received SPI: ");
  Serial.println(out);
  return true;
}

// ROBUST SERVO MOTION CONTROL FUNCTIONS

/**
 * Sweeps a given Servo object smoothly back to its 0-degree origin (544 µs).
 * Uses a reference (&) parameter to prevent object copying.
 */
void servoToOrigin(Servo &servo) {
  int currentPulse = servo.readMicroseconds();
  
  if (currentPulse == ORIGIN_PULSE) {
    return; 
  }

  if (currentPulse < ORIGIN_PULSE) {
    for (int p = currentPulse; p <= ORIGIN_PULSE; p++) {
      servo.writeMicroseconds(p);
      delayMicroseconds(1500); // Step delay controlling speed and current limit
    }
  } else {
    for (int p = currentPulse; p >= ORIGIN_PULSE; p--) {
      servo.writeMicroseconds(p);
      delayMicroseconds(1500); // Step delay controlling speed and current limit
    }
  }
}

/**
 * Sweeps a given Servo object smoothly to a targeted angle and holds it.
 * @param servo Referenced Servo object.
 * @param angle Target position in degrees (0 to 180).
 */
void servoToAngle(Servo &servo, int angle) {
  // Standard conversion mapping from geometric degrees to microsecond pulse timings
  int targetPulse = map(angle, 0, 180, ORIGIN_PULSE, MAX_PULSE);
  targetPulse = constrain(targetPulse, ORIGIN_PULSE, MAX_PULSE);

  int currentPulse = servo.readMicroseconds();

  if (currentPulse < targetPulse) {
    for (int p = currentPulse; p <= targetPulse; p++) {
      servo.writeMicroseconds(p);
      delayMicroseconds(500); 
    }
  } else {
    for (int p = currentPulse; p >= targetPulse; p--) {
      servo.writeMicroseconds(p);
      delayMicroseconds(2000);
    }
  }
  delay(1000);
}