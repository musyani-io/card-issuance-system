#include <Arduino.h>
#include <Servo.h>

// Object definitions
Servo servo1;

// Variable definition
#define SERVO1 2
#define SERVO2 3

// Functions
void checkServo(Servo servo);

void setup() {

  // Serial initialization
  Serial.begin(115200);
  delayMicroseconds(10);

  // Servo motor
  servo1.attach(SERVO1);
  checkServo(servo1);

}

void loop() {}

void toOriginal(Servo servo) {
  // To 0 degrees angle

  servo.write(0);
  Serial.println("To original!");
  delayMicroseconds(50);

}
