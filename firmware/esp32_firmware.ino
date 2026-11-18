/*
 * ============================================================================
 * TROLLEYWISE SMART SHOPPING CART - ESP32 EMBEDDED SENSOR FIRMWARE
 * Multimodal Acquisition: 4x Load Cells (HX711) + 6-DOF IMU (MPU-6050)
 * ============================================================================
 * Target Microcontroller: ESP32-WROOM-32 / ESP32-S3
 * Communication: Wi-Fi WebSocket / HTTP REST + USB-CDC Hardware Serial
 * Protocol: Documented JSON Telemetry Payload
 */

#include <WiFi.h>
#include <Wire.h>
#include <ArduinoJson.h> // v6 or v7

// ---------------------- PIN DEFINITIONS ----------------------
// HX711 Load Cell Interface (Wheatstone Bridge ADC)
#define HX711_DOUT_PIN  19
#define HX711_SCK_PIN   18

// MPU-6050 IMU Interface (I2C)
#define I2C_SDA_PIN     21
#define I2C_SCL_PIN     22
#define MPU6050_ADDR    0x68

// Status LED / Buzzer
#define STATUS_LED_PIN  2
#define BUZZER_PIN      4

// ---------------------- NETWORK CONFIGURATION ----------------------
const char* WIFI_SSID     = "TrolleyWise_Store_WLAN";
const char* WIFI_PASSWORD = "StoreSmartCart2026";
const char* EDGE_HOST     = "192.168.1.100"; // NVIDIA Jetson Orin Nano / Local Server
const int   EDGE_PORT     = 8000;

// Device Identification
const char* DEVICE_UUID   = "TROLLEY-01";
const char* FIRMWARE_VER  = "2.4.1";

// ---------------------- CALIBRATION CONSTANTS ----------------------
float calibration_factor  = -21.45; // Calibrated for 4x 50kg load cells in parallel
long  zero_offset         = 0;

// Weight baseline & filtering
const int FILTER_WINDOW_SIZE = 10;
float weight_samples[FILTER_WINDOW_SIZE];
int   filter_index = 0;
float stable_weight = 0.0;
float last_raw_weight = 0.0;

// IMU Motion Thresholds
const float MOTION_ACCEL_THRESHOLD = 0.35; // m/s^2 jitter threshold
const float MOTION_GYRO_THRESHOLD  = 5.0;  // deg/s angular velocity

// ---------------------- MPU-6050 REGISTER MAP ----------------------
void initMPU6050() {
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x6B); // PWR_MGMT_1
  Wire.write(0x00); // Wake up MPU-6050
  Wire.endTransmission(true);
}

void readIMU(float &ax, float &ay, float &az, float &gx, float &gy, float &gz, bool &is_moving) {
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU6050_ADDR, 14, true);

  if (Wire.available() >= 14) {
    int16_t raw_ax = (Wire.read() << 8) | Wire.read();
    int16_t raw_ay = (Wire.read() << 8) | Wire.read();
    int16_t raw_az = (Wire.read() << 8) | Wire.read();
    int16_t raw_temp = (Wire.read() << 8) | Wire.read();
    int16_t raw_gx = (Wire.read() << 8) | Wire.read();
    int16_t raw_gy = (Wire.read() << 8) | Wire.read();
    int16_t raw_gz = (Wire.read() << 8) | Wire.read();

    // Scale to standard units (±2g, ±250 deg/s)
    ax = (float)raw_ax / 16384.0 * 9.80665;
    ay = (float)raw_ay / 16384.0 * 9.80665;
    az = (float)raw_az / 16384.0 * 9.80665;
    gx = (float)raw_gx / 131.0;
    gy = (float)raw_gy / 131.0;
    gz = (float)raw_gz / 131.0;

    // Check dynamic acceleration (subtract 1g gravity component)
    float dynamic_accel = sqrt(pow(ax, 2) + pow(ay, 2) + pow(az - 9.80665, 2));
    float angular_rate  = sqrt(pow(gx, 2) + pow(gy, 2) + pow(gz, 2));

    is_moving = (dynamic_accel > MOTION_ACCEL_THRESHOLD) || (angular_rate > MOTION_GYRO_THRESHOLD);
  } else {
    // Fallback if sensor read fails
    ax = 0.0; ay = 0.0; az = 9.81;
    gx = 0.0; gy = 0.0; gz = 0.0;
    is_moving = false;
  }
}

// ---------------------- BIT-BANG HX711 READ ----------------------
long readHX711Raw() {
  long count = 0;
  pinMode(HX711_DOUT_PIN, INPUT);
  pinMode(HX711_SCK_PIN, OUTPUT);
  digitalWrite(HX711_SCK_PIN, LOW);

  unsigned long start = millis();
  while (digitalRead(HX711_DOUT_PIN) == HIGH) {
    if (millis() - start > 100) return 0; // Timeout
  }

  for (int i = 0; i < 24; i++) {
    digitalWrite(HX711_SCK_PIN, HIGH);
    delayMicroseconds(1);
    count = count << 1;
    digitalWrite(HX711_SCK_PIN, LOW);
    delayMicroseconds(1);
    if (digitalRead(HX711_DOUT_PIN)) {
      count++;
    }
  }

  // 25th pulse for 128 gain (Channel A)
  digitalWrite(HX711_SCK_PIN, HIGH);
  delayMicroseconds(1);
  digitalWrite(HX711_SCK_PIN, LOW);
  delayMicroseconds(1);

  // Sign extension for 24-bit 2's complement
  if (count & 0x800000) {
    count |= 0xFF000000;
  }
  return count;
}

float getFilteredWeight() {
  long raw = readHX711Raw();
  float weight_g = (float)(raw - zero_offset) / calibration_factor;
  if (weight_g < 0.0) weight_g = 0.0; // Floor zero drift

  weight_samples[filter_index] = weight_g;
  filter_index = (filter_index + 1) % FILTER_WINDOW_SIZE;

  // Compute moving average
  float sum = 0.0;
  for (int i = 0; i < FILTER_WINDOW_SIZE; i++) {
    sum += weight_samples[i];
  }
  return sum / (float)FILTER_WINDOW_SIZE;
}

void setup() {
  Serial.begin(115200);
  pinMode(STATUS_LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, HIGH);

  // Initialize sensors
  initMPU6050();

  // Zero / Tare load cells
  long sum = 0;
  for (int i = 0; i < 20; i++) {
    sum += readHX711Raw();
    delay(10);
  }
  zero_offset = sum / 20;

  for (int i = 0; i < FILTER_WINDOW_SIZE; i++) {
    weight_samples[i] = 0.0;
  }

  Serial.println("{\"status\":\"ESP32_INITIALIZED\",\"device_uuid\":\"TROLLEY-01\"}");
}

void loop() {
  float current_weight = getFilteredWeight();
  float ax, ay, az, gx, gy, gz;
  bool is_moving;
  readIMU(ax, ay, az, gx, gy, gz, is_moving);

  // Determine stability: small weight derivative and cart stationary
  bool is_stable = !is_moving && (fabs(current_weight - last_raw_weight) < 2.0);
  last_raw_weight = current_weight;

  // Build documented JSON message payload
  StaticJsonDocument<384> doc;
  doc["device_uuid"]       = DEVICE_UUID;
  doc["timestamp"]         = millis();
  doc["raw_weight_grams"]  = current_weight;
  doc["filtered_weight_g"] = current_weight;
  doc["is_stable"]         = is_stable;

  JsonObject imu = doc.createNestedObject("imu");
  imu["accel_x"]   = ax;
  imu["accel_y"]   = ay;
  imu["accel_z"]   = az;
  imu["gyro_x"]    = gx;
  imu["gyro_y"]    = gy;
  imu["gyro_z"]    = gz;
  imu["is_moving"] = is_moving;

  // Transmit telemetry over Serial (or Wi-Fi WebSocket)
  serializeJson(doc, Serial);
  Serial.println();

  delay(100); // 10Hz sampling rate
}
