#include <Arduino.h>
#include <Servo.h>
#include <SPI.h>

// Object definitions
Servo servo1;


// Variable definition
#define SERVO1 2
#define DIR_PIN 22
#define STEP_PIN 24 
#define ENABLE_PIN 23
#define SCK_PIN 52
#define SS_PIN 53
#define MISO_PIN 50
#define MOSI_PIN 51

// Constants
const int L_SERVO = 600;
const int R_SERVO = 2400;
const int C_SERVO = 1600;
const int STEPS_PER_REV = 200;
volatile byte recievedByte;
volatile bool newData = false;

// Commands 

// Functions
void rotateSteps(int steps);
ISR(SPI_STC_vect) {
  recievedByte = SPDR;
  newData = true;
}

void setup() {

  // Serial initialization
  Serial.begin(115200);
  delayMicroseconds(10);

  // Pin definition
  pinMode(DIR_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  pinMode(ENABLE_PIN, OUTPUT);
  pinMode(MISO_PIN, OUTPUT);
  pinMode(SS_PIN, INPUT);

  // Servo motor
  servo1.attach(SERVO1);
  servo1.writeMicroseconds(C_SERVO); // to center
  delayMicroseconds(50);

  // SPI communication
  SPCR |= _BV(SPE);
  SPI.attachInterrupt();
  delay(1000);
  Serial.println("SPI Initiated!");

}

void loop() {
  if (newData) {
    newData = false;

    Serial.print("Recieved from Pi: ");
    Serial.println((char)recievedByte);
  }
}

void rotateSteps(int steps) {
  digitalWrite(ENABLE_PIN, LOW);
  digitalWrite(DIR_PIN, HIGH);
  delayMicroseconds(20);

  for (int i = 0; i < steps; i++) {

    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(5000);
    digitalWrite(STEP_PIN, LOW);
    delayMicroseconds(5000);

    Serial.println(i);
  }
}