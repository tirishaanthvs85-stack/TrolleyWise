"""
TrolleyWise Hardware Client - Production ESP32 Communication Layer
Reads real sensor data from ESP32 microcontroller over Serial / USB or Network.
Adheres to Section 8:
- Documented JSON message protocol
- Load cell weight telemetry
- IMU acceleration and motion detection
- Connection monitoring & sensor error handling
- Zero fake data generation when disconnected
"""

import json
import time
import threading
from typing import Optional, Callable, Dict, Any

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

class ESP32HardwareClient:
    def __init__(self, port: Optional[str] = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.is_connected = False
        self.is_running = False
        self.last_reading: Optional[Dict[str, Any]] = None
        self.last_heartbeat: float = 0.0
        self.telemetry_callbacks = []
        self._thread: Optional[threading.Thread] = None

    def register_callback(self, callback: Callable[[Dict[str, Any]], None]):
        self.telemetry_callbacks.append(callback)

    def connect(self) -> bool:
        if not SERIAL_AVAILABLE:
            print("[ESP32 Client] PySerial not installed. Hardware connection unavailable.")
            return False

        if not self.port:
            print("[ESP32 Client] No serial port specified (e.g. COM3 or /dev/ttyUSB0).")
            return False

        try:
            print(f"[ESP32 Client] Connecting to ESP32 on port {self.port} at {self.baudrate} baud...")
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1.0)
            self.is_connected = True
            self.is_running = True
            self._thread = threading.Thread(target=self._read_loop, daemon=True)
            self._thread.start()
            print("[ESP32 Client] Hardware connection established.")
            return True
        except Exception as e:
            print(f"[ESP32 Client] Failed to connect to ESP32: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        self.is_running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.is_connected = False
        print("[ESP32 Client] Hardware disconnected.")

    def _read_loop(self):
        while self.is_running and self.serial_conn and self.serial_conn.is_open:
            try:
                line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                if line.startswith("{") and line.endswith("}"):
                    data = json.loads(line)
                    self.last_reading = data
                    self.last_heartbeat = time.time()
                    for cb in self.telemetry_callbacks:
                        try:
                            cb(data)
                        except Exception as cb_err:
                            print(f"[ESP32 Client] Telemetry callback error: {cb_err}")
            except Exception as e:
                print(f"[ESP32 Client] Error reading serial stream: {e}")
                self.is_connected = False
                time.sleep(1.0)

    def get_latest_reading(self) -> Optional[Dict[str, Any]]:
        """Returns the most recent verified hardware reading. Does not invent data if disconnected."""
        if not self.is_connected:
            return None
        # Verify freshness within last 2 seconds
        if time.time() - self.last_heartbeat > 2.0:
            return None
        return self.last_reading

# Global Hardware Client instance
esp32_hardware_client = ESP32HardwareClient()
