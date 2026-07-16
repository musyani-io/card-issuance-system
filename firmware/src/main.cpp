#include <Arduino.h>
#include <Servo.h>
#include <SPI.h>
#include <Stepper.h>
#include <string.h>

// 28BYJ-48 Stepper & Driver Pin Mapping
#define STEP_IN1 30
#define STEP_IN2 31
#define STEP_IN3 32
#define STEP_IN4 33

// Objects
Servo servo1; // Card holder (Pin 22)

// Pin definitions
#define SERVO1 22

// Stepper Motor Configuration
constexpr int STEPS_PER_REV = 2048; 
constexpr int STEP_SPEED_RPM = 5;   // Reduced to 5 RPM to maximize torque and prevent card slippage

// Absolute Stepper Targets (Entrance Positions)
constexpr int STEP_POS_A = 0;    // Compartment A: 0°
constexpr int STEP_POS_B = 683;  // Compartment B: 120°
constexpr int STEP_POS_C = 1365; // Compartment C: 240° (Also acts as Failure/Reject slot)

// Absolute Stepper Targets (Exit Positions = Entrance + 1024 steps)
constexpr int STEP_EXIT_A = 1024; // Compartment A at Exit (180°)
constexpr int STEP_EXIT_B = 1707; // Compartment B at Exit (120° + 180° = 300°)

// State Tracking
int currentStep = 0; // Tracks absolute stepper position relative to home (A)

// Note: Pin order must be (IN1, IN3, IN2, IN4) for 28BYJ-48 sequence
Stepper stepper(STEPS_PER_REV, STEP_IN1, STEP_IN3, STEP_IN2, STEP_IN4);

// Hardware SPI pins on the Mega 2560
constexpr uint8_t SPI_SS_PIN = 53;
constexpr uint8_t SPI_MOSI_PIN = 51;
constexpr uint8_t SPI_MISO_PIN = 50;
constexpr uint8_t SPI_SCK_PIN = 52;

// SPI status frames from Raspberry Pi: "1X" for Entrance, "2X" for Exit, "00" for OCR Error
constexpr uint8_t SPI_FRAME_LEN = 2;

volatile char spiFrame[SPI_FRAME_LEN + 1] = {0};
volatile uint8_t spiFrameIndex = 0;
volatile bool spiFrameReady = false;

// Servo Pulse Constants
constexpr int ORIGIN_PULSE = 544;  
constexpr int MAX_PULSE = 2400;    

// Functions
void setupSpiReceiver();
bool receiveSpiMessage(char *out, size_t outSize);
void servoToOrigin(Servo &servo);
void servoToAngle(Servo &servo, int angle);
void moveStepperToStep(int targetStep);

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

  // Initialize Stepper Motor Speed
  stepper.setSpeed(STEP_SPEED_RPM);

  // Pre-load the 0-degree pulse width BEFORE attaching to prevent startup jumps
  servo1.writeMicroseconds(ORIGIN_PULSE);
  delayMicroseconds(10);

  // Attach card holder servo
  servo1.attach(SERVO1);
  delayMicroseconds(100);

  // Verify homing alignment softly
  Serial.println("Homing verification...");
  servoToOrigin(servo1);

  // Boot assumption: Carousel is physically aligned to Compartment A (0 deg)
  currentStep = STEP_POS_A;

  Serial.println("System Ready! Awaiting SPI commands...");
}

void loop() {
  // Clear software buffer whenever the Pi releases Chip Select (SS Pin goes HIGH)
  if (digitalRead(SPI_SS_PIN) == HIGH) {
    spiFrameIndex = 0;
  }
  
  char spiMessage[SPI_FRAME_LEN + 1];

  if (receiveSpiMessage(spiMessage, sizeof(spiMessage))) {
    
    // --- ENTRANCE & FAILURE ROUTINES ("1X" / "00") ---
    
    if (strcmp(spiMessage, "10") == 0) {
      Serial.println("Target: Compartment A -> Entrance (0 deg)");
      moveStepperToStep(STEP_POS_A);
      delay(2000); 
      
      servoToAngle(servo1, 70);
      delay(1000); 
      servoToOrigin(servo1);
    } 
    else if (strcmp(spiMessage, "11") == 0) {
      Serial.println("Target: Compartment B -> Entrance (120 deg)");
      moveStepperToStep(STEP_POS_B);
      delay(2000); 
      
      servoToAngle(servo1, 70);
      delay(1000); 
      servoToOrigin(servo1);
      
      // Return carousel to OG position (Compartment A)
      moveStepperToStep(STEP_POS_A); 
      delay(2000); 
    }
    else if (strcmp(spiMessage, "12") == 0 || strcmp(spiMessage, "00") == 0) {
      if (strcmp(spiMessage, "00") == 0) {
        Serial.println("Target: OCR Error/Failure -> Routing to Compartment C (240 deg)");
      } else {
        Serial.println("Target: Compartment C -> Entrance (240 deg)");
      }
      moveStepperToStep(STEP_POS_C);
      delay(2000); 
      
      servoToAngle(servo1, 70);
      delay(1000); 
      servoToOrigin(servo1);
      
      // Return carousel to OG position (Compartment A)
      moveStepperToStep(STEP_POS_A); 
      delay(2000); 
    } 

    // --- EXIT ROUTINES ("2X") ---
    
    else if (strcmp(spiMessage, "20") == 0) {
      Serial.println("Target: Compartment A -> Exit (180 deg)");
      moveStepperToStep(STEP_EXIT_A);
      delay(2000); // Settle time at physical exit (Servo 1 does nothing)
      
      // Return carousel to OG position (Compartment A)
      moveStepperToStep(STEP_POS_A);
      delay(2000);
    }
    else if (strcmp(spiMessage, "21") == 0) {
      Serial.println("Target: Compartment B -> Exit (300 deg)");
      moveStepperToStep(STEP_EXIT_B);
      delay(2000); // Settle time at physical exit (Servo 1 does nothing)
      
      // Return carousel to OG position (Compartment A)
      moveStepperToStep(STEP_POS_A);
      delay(2000);
    }
    else {
      Serial.print("Unknown SPI Frame: ");
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

// ROBUST STEPPER MOTION CONTROL FUNCTION

void moveStepperToStep(int targetStep) {
  int stepsToMove = targetStep - currentStep;
  
  if (stepsToMove != 0) {
    Serial.print("Moving stepper from ");
    Serial.print(currentStep);
    Serial.print(" to ");
    Serial.print(targetStep);
    Serial.print(" (Steps: ");
    Serial.print(stepsToMove);
    Serial.println(")");
    
    stepper.step(stepsToMove);
    currentStep = targetStep;
  }
}

// ROBUST SERVO MOTION CONTROL FUNCTIONS

void servoToOrigin(Servo &servo) {
  int currentPulse = servo.readMicroseconds();
  
  if (currentPulse == ORIGIN_PULSE) {
    return; 
  }

  if (currentPulse < ORIGIN_PULSE) {
    for (int p = currentPulse; p <= ORIGIN_PULSE; p++) {
      servo.writeMicroseconds(p);
      delayMicroseconds(1500); 
    }
  } else {
    for (int p = currentPulse; p >= ORIGIN_PULSE; p--) {
      servo.writeMicroseconds(p);
      delayMicroseconds(1500); 
    }
  }
}

void servoToAngle(Servo &servo, int angle) {
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