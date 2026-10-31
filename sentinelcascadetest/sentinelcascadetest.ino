#include <Wire.h>                    // library for the two-lane I2C road

void setup() {
  Serial.begin(115200);              // open the text window to your PC
  Wire.begin(21, 22);                // start I2C: SDA = GPIO21, SCL = GPIO22
  delay(1000);                       // wait a second for things to settle
  Serial.println("Scanning...");
}

void loop() {
  int found = 0;                     // how many devices answered
  for (byte addr = 1; addr < 127; addr++) {   // knock on every door
    Wire.beginTransmission(addr);    // call this address
    if (Wire.endTransmission() == 0) {          // 0 means "someone answered"
      Serial.print("Found device at 0x");
      Serial.println(addr, HEX);     // print the address in hex
      found++;
    }
  }
  if (found == 0) Serial.println("Nothing found");
  Serial.println("---");
  delay(3000);                       // scan again in 3 seconds
}
