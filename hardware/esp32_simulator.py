"""
================================================================================
[EXPLICITLY LABELLED: TROLLEYWISE SENSOR HARDWARE SIMULATOR - DEV/TEST ONLY]
================================================================================
Notice: This module generates synthetic telemetry exclusively for development,
automated testing, and offline algorithm simulation.
It is NOT real hardware data and MUST NOT be used to represent physical sensor validation.
"""

import time
import random
from typing import Dict, Any

class ESP32HardwareSimulator:
    def __init__(self, device_uuid: str = "TROLLEY-01"):
        self.device_uuid = device_uuid
        self.current_weight = 0.0
        self.is_moving = False
        self.noise_std_dev = 0.5 # Gaussian noise on load cells

    def set_weight(self, weight_grams: float, is_moving: bool = False):
        """Sets the ground-truth simulated load on the virtual basket."""
        self.current_weight = max(0.0, float(weight_grams))
        self.is_moving = is_moving

    def add_weight(self, delta_grams: float, is_moving: bool = False):
        self.set_weight(self.current_weight + delta_grams, is_moving)

    def remove_weight(self, delta_grams: float, is_moving: bool = False):
        self.set_weight(max(0.0, self.current_weight - delta_grams), is_moving)

    def generate_reading(self) -> Dict[str, Any]:
        """Generates a synthetic telemetry payload with realistic physical noise."""
        noise = random.gauss(0, self.noise_std_dev)
        raw_w = max(0.0, round(self.current_weight + noise, 2))
        filtered_w = round(self.current_weight, 2)

        if self.is_moving:
            ax = round(random.uniform(-1.5, 1.5), 3)
            ay = round(random.uniform(-1.5, 1.5), 3)
            az = round(9.81 + random.uniform(-2.0, 2.0), 3)
            gx = round(random.uniform(-15.0, 15.0), 2)
            gy = round(random.uniform(-15.0, 15.0), 2)
            gz = round(random.uniform(-15.0, 15.0), 2)
            is_stable = False
        else:
            ax = round(random.uniform(-0.05, 0.05), 3)
            ay = round(random.uniform(-0.05, 0.05), 3)
            az = round(9.81 + random.uniform(-0.05, 0.05), 3)
            gx = round(random.uniform(-0.5, 0.5), 2)
            gy = round(random.uniform(-0.5, 0.5), 2)
            gz = round(random.uniform(-0.5, 0.5), 2)
            is_stable = True

        return {
            "device_uuid": self.device_uuid,
            "timestamp": int(time.time() * 1000),
            "raw_weight_grams": raw_w,
            "filtered_weight_grams": filtered_w,
            "is_stable": is_stable,
            "source": "[SIMULATED_DEV_DATA_ONLY]",
            "imu": {
                "accel_x": ax,
                "accel_y": ay,
                "accel_z": az,
                "gyro_x": gx,
                "gyro_y": gy,
                "gyro_z": gz,
                "is_moving": self.is_moving
            }
        }
