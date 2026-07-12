#include <Arduino.h>
#include <Servo.h>
#include <SPI.h>

// Objects
Servo servo1; // card holder
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

// Variables
const int MIN_PULSE = 550;
const int PULSE_BAL = 1000;
const int MID_PULSE = 1600;
const int PULSE_45 = 1300;
const int STEP_REV = 200;
int currAngle = 0;

// Functions
void servoTo45(Servo servo);
void servoToAngle(Servo servo, int angle);
void setupSpiReceiver();
bool receiveSpiMessage(char *out, size_t outSize);

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

  // Motors
  servo1.attach(SERVO1);
  servo2.attach(SERVO2);
  servoTo45(servo1);
  servo2.writeMicroseconds(MIN_PULSE);

  Serial.println("Servos OG!");
  delay(3000);
}

void loop() {
  
  if (digitalRead(SPI_SS_PIN) == HIGH) {
    spiFrameIndex = 0;
  }
  
  char spiMessage[SPI_FRAME_LEN + 1];

  if (receiveSpiMessage(spiMessage, sizeof(spiMessage))) {
    // Message processed inside receiveSpiMessage()
  }
}

// FUNCTIONS

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

void servoTo45(Servo servo) {
  int pos = 0;

  for (int i = PULSE_BAL; i < PULSE_45; i++) {  // Center to 45
    servo.writeMicroseconds(i);
    delayMicroseconds(4000);
    pos = i;
  }
  Serial.println("To 45....");
  delay(3000);

  for (int i = pos; i > 0; i--) {   // 45 to upper - card release
    servo.writeMicroseconds(i);
    delayMicroseconds(1500);
    pos = i;
  }
  Serial.println("Back to -45....");
  delay(1000);

  servo.writeMicroseconds(PULSE_BAL);
  for (int i = pos; i < PULSE_BAL; i++) {   // Back to center
    servo.writeMicroseconds(i);
    delayMicroseconds(1000);
  }
  Serial.println("Back to level!");
}

void servoToAngle(Servo servo, int angle) {
  int pulse = MIN_PULSE + ((1850 / 180) * angle);

  for (int i = MIN_PULSE ; i < pulse; i++) {
    servo.writeMicroseconds(i);
    delayMicroseconds(1500);
  }

  delay(2500);

  for (int i = pulse; i > MIN_PULSE; i--) {
    servo.writeMicroseconds(i);
    delayMicroseconds(1500);
  }
}