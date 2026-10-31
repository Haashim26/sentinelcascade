#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ---------- pins ----------
const int RAIN_PIN = 35, TEMP_PIN = 4, BUTTON_PIN = 18;
const int MPU_ADDR = 0x68;

// ---------- thresholds (from our experiments) ----------
const int   RAIN_DROP   = 700;    // below baseline = wet
const int   RAIN_NEED   = 3;      // consecutive hits
const float SHAKE_LINE  = 0.10;   // vibration peak line
const int   VIB_NEED    = 2;
const float TEMP_RISE   = 3.0;    // degrees above baseline
const unsigned long BASELINE_MS = 10000;
const int W = 5;                  // window size

OneWire oneWire(TEMP_PIN);
DallasTemperature tempSensor(&oneWire);

// ---------- state ----------
int rainBuf[W] = {0}, rIdx = 0, rFilled = 0, rHits = 0;
float vibBuf[W] = {0}; int vIdx = 0, vFilled = 0, vHits = 0;
float lastMag = 1.0;
float rainBase = 0, tempBase = 0; long rainSum = 0; float tempSum = 0;
int rainCnt = 0, tempCnt = 0;
bool baselineDone = false;
float tempC = 25.0;
unsigned long startMs, lastTempMs = 0;

int medianOf(int *a, int n) {
  int t[W];
  for (int i = 0; i < n; i++) t[i] = a[i];
  for (int i = 1; i < n; i++) {
    int k = t[i], j = i - 1;
    while (j >= 0 && t[j] > k) { t[j + 1] = t[j]; j--; }
    t[j + 1] = k;
  }
  return t[n / 2];
}

float readShake() {                       // MPU6050 change in total strength
  Wire.beginTransmission(MPU_ADDR); Wire.write(0x3B); Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 6);
  int16_t ax = Wire.read() << 8 | Wire.read();
  int16_t ay = Wire.read() << 8 | Wire.read();
  int16_t az = Wire.read() << 8 | Wire.read();
  float x = ax / 16384.0, y = ay / 16384.0, z = az / 16384.0;
  float mag = sqrt(x * x + y * y + z * z);
  float s = fabs(mag - lastMag);
  lastMag = mag;
  return s;
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  Wire.begin(21, 22);
  Wire.beginTransmission(MPU_ADDR); Wire.write(0x6B); Wire.write(0); Wire.endTransmission();
  tempSensor.begin();
  tempSensor.setWaitForConversion(false);  // don't block the loop
  tempSensor.requestTemperatures();
  startMs = millis();
  Serial.println("Learning baselines for 10 s (rain dry, board still)...");
}

void loop() {
  // --- read sensors ---
  int rain = analogRead(RAIN_PIN);
  float shake = readShake();
  bool button = (digitalRead(BUTTON_PIN) == LOW);

  if (millis() - lastTempMs >= 1000) {     // temp once per second
    float c = tempSensor.getTempCByIndex(0);
    if (c > -50 && c < 100) tempC = c;
    tempSensor.requestTemperatures();
    lastTempMs = millis();
  }

  // --- rolling windows ---
  rainBuf[rIdx] = rain; rIdx = (rIdx + 1) % W; if (rFilled < W) rFilled++;
  vibBuf[vIdx] = shake; vIdx = (vIdx + 1) % W; if (vFilled < W) vFilled++;
  int rainMed = medianOf(rainBuf, rFilled);
  float vibPeak = 0;
  for (int i = 0; i < vFilled; i++) if (vibBuf[i] > vibPeak) vibPeak = vibBuf[i];

  // --- learn baselines ---
  if (!baselineDone) {
    rainSum += rain; rainCnt++;
    tempSum += tempC; tempCnt++;
    if (millis() - startMs >= BASELINE_MS) {
      rainBase = (float)rainSum / rainCnt;
      tempBase = tempSum / tempCnt;
      baselineDone = true;
      Serial.print("Baselines: rain="); Serial.print(rainBase, 0);
      Serial.print(" temp="); Serial.println(tempBase, 1);
    }
    delay(50);
    return;
  }

  // --- elevated flags ---
  rHits = (rainMed < rainBase - RAIN_DROP) ? rHits + 1 : 0;
  vHits = (vibPeak > SHAKE_LINE) ? vHits + 1 : 0;
  bool rainEl = rHits >= RAIN_NEED;
  bool vibEl  = vHits >= VIB_NEED;
  bool tempEl = tempC > tempBase + TEMP_RISE;
  int vibScaled = (int)constrain(vibPeak / 1.5 * 4095.0, 0, 4095);

  Serial.print("vib="); Serial.print(vibScaled);  Serial.print(vibEl ? "[E] " : "[ ] ");
  Serial.print("temp="); Serial.print(tempC, 1); Serial.print(tempEl ? "[E] " : "[ ] ");
  Serial.print("rain="); Serial.print(rainMed);  Serial.print(rainEl ? "[E] " : "[ ] ");
  Serial.print("button="); Serial.println(button ? "PRESSED" : "no");
  delay(50);
}