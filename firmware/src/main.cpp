#include <Arduino.h>
#include <Servo.h>

// Object definitions
Servo servo1;

// Variable definition
#define SERVO1 2
#define SERVO2 3

// Constants
const int L_SERVO = 600;
const int R_SERVO = 2400;
const int C_SERVO = 1600;

// Functions

void setup() {

  // Serial initialization
  Serial.begin(115200);
  delayMicroseconds(10);

  // Servo motor
  servo1.attach(SERVO1);
  servo1.writeMicroseconds(C_SERVO); // to center

}

void loop() {}
