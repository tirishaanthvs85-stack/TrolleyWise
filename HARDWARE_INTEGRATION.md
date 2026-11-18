# TrolleyWise Hardware Integration Guide

## 1. System Hardware Components
- **Microcontroller:** ESP32-WROOM-32 / ESP32-S3 (240MHz dual-core, 802.11 b/g/n Wi-Fi, BLE).
- **Weight Sensing:** 4x 50kg Half-Bridge Load Cells configured in a full Wheatstone Bridge on the trolley basket frame.
- **Amplifier & ADC:** HX711 24-bit Differential ADC module (Gain 128 on Channel A).
- **Motion Sensor:** MPU-6050 6-Axis Inertial Measurement Unit (I2C: 3-axis accelerometer + 3-axis gyroscope).
- **Vision Subsystem:** Top-down RGB camera (60fps wide angle) + side rim camera connected to edge computer.
- **Edge Computing Platform:** NVIDIA Jetson Orin Nano / Orin NX / Embedded x86 gateway.
- **Customer Display:** 10.1-inch IPS Capacitive Touchscreen (1920x1200).

---

## 2. Wiring & Pinout

| ESP32 Pin | Peripheral Pin | Function |
|---|---|---|
| GPIO 19 | HX711 DOUT | Serial Data Out |
| GPIO 18 | HX711 SCK | Serial Clock Out |
| GPIO 21 | MPU6050 SDA | I2C Data Line |
| GPIO 22 | MPU6050 SCL | I2C Clock Line |
| GPIO 2 | Status LED | Heartbeat Indicator |
| GPIO 4 | Buzzer | Verification Audio Prompt |
| 5V / 3V3 | VCC | System Power Rails |
| GND | GND | Common Ground |

---

## 3. Communication Protocol (JSON Telemetry)

The ESP32 communicates with the edge server over Serial USB (`/dev/ttyUSB0` or `COM3`) or Wi-Fi WebSocket at 10 Hz:

```json
{
  "device_uuid": "TROLLEY-01",
  "timestamp": 1700201948201,
  "raw_weight_grams": 515.2,
  "filtered_weight_grams": 515.0,
  "is_stable": true,
  "imu": {
    "accel_x": 0.012,
    "accel_y": 0.018,
    "accel_z": 9.805,
    "gyro_x": 0.12,
    "gyro_y": -0.08,
    "gyro_z": 0.05,
    "is_moving": false
  }
}
```

---

## 4. Hardware Client vs Development Simulator
- **Production Adapter:** `hardware/esp32_client.py` connects to live USB Serial or network stream. Does **NOT** fabricate sensor readings when disconnected.
- **Development Simulator:** `hardware/esp32_simulator.py` is explicitly labelled for testing algorithms offline and in unit tests.
