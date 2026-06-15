#include <Arduino.h>
#include <Servo.h>

// Library definition
Servo servo1;

// PIN definition
#define SERVO1_PIN 2

// Function checks
void servoCheck(Servo servo_t);

void setup() {

  // Serial monitor
  Serial.begin(115200);
  Serial.println("Low-level control initiating.....")

  // Motor initialization
  servo1.attach(SERVO1_PIN);
  servoCheck(servo1);

  delay(1000);
}

void loop() {}

void servoCheck(Servo servo_t) {

  servo_t.write(90);
  delay(250);
  servo_t.write(0);
  delay(250);

}
