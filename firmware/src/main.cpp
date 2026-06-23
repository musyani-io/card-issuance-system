#include <Arduino.h>
#include <Servo.h>

// Object definitions
Servo servo1;

// Variable definition
#define PWR 13
#define SERVO1 2
#define SERVO2 3
#define DIR_PIN 22
#define STEP_PIN 23
#define ENABLE_PIN 24

// Constants
const int L_SERVO = 600;
const int R_SERVO = 2400;
const int C_SERVO = 1600;

// Functions

void setup() {

  // Serial initialization
  Serial.begin(115200);
  delayMicroseconds(10);

  // Alternate power
  pinMode(PWR, OUTPUT);
  digitalWrite(PWR, HIGH);

  // Servo motor
  servo1.attach(SERVO1);
  servo1.writeMicroseconds(C_SERVO); // to center
  delayMicroseconds(50);

  // Stepper motor
  pinMode(ENABLE_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);

  digitalWrite(ENABLE_PIN, LOW);
  digitalWrite(STEP_PIN, LOW);
  digitalWrite(DIR_PIN, LOW);
  delayMicroseconds(50);
  Serial.println("Stepper stop!");

  for (int i = 0; i < 200; i++) {
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(1000);
    digitalWrite(STEP_PIN, LOW);
    delayMicroseconds(1000);

    Serial.println("1 step...");
  }

}

void loop() {}
