#include <Arduino.h>
#include <Servo.h>

// On the Arduino Mega 2560, D7 maps directly to digital pin 7
#define SERVO_PIN 22

Servo testServo;

void setup() {
    testServo.attach(SERVO_PIN);
}

void loop() {

}