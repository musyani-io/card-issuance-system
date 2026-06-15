#include <Arduino.h>


void setup() {
  Serial.begin(115200);
  Serial.println("Mega ON!")

  digitalWrite(LED_BUILTIN, 0);

  delay(2000);
}

void loop() {

  digitalWrite(LED_BUILTIN, 1)
  Serial.println("LED ON!")
  delay(1000)
  digitalWrite(LED_BUILTIN, 0)
  Serial.println("LED OFF")
  delay(1000);

}
