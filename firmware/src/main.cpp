#include <Arduino.h>
#include <Servo.h>

// Object definitions
Servo servo1;

// Variable definition
#define SERVO1 2
#define DIR_PIN 22 // Green wire
#define STEP_PIN 24 // Purple wire
#define ENABLE_PIN 23 // Blue wire

// Constants
const int L_SERVO = 600;
const int R_SERVO = 2400;
const int C_SERVO = 1600;
const int STEPS_PER_REV = 200;

// Functions
void rotateSteps(int steps);

void setup() {

  // Serial initialization
  Serial.begin(115200);
  delayMicroseconds(10);

  // Pin definition
  pinMode(DIR_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  pinMode(ENABLE_PIN, OUTPUT);

  // Servo motor
  servo1.attach(SERVO1);
  servo1.writeMicroseconds(C_SERVO); // to center
  delayMicroseconds(50);

  // Stepper motor
  digitalWrite(ENABLE_PIN, LOW);
  rotateSteps(STEPS_PER_REV);
  Serial.println("Stepper holds!");

}

void loop() {}

void rotateSteps(int steps) {
  delayMicroseconds(10);

  for (int i = 0; i < steps; i++) {

    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(1000);
    digitalWrite(STEP_PIN, LOW);
    delayMicroseconds(1000);

    Serial.print("+1");
  }
}