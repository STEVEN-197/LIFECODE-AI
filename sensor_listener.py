"""
ESP32 USB Serial Sensor Listener
Auto-detects COM port, reads heart_rate, gsr, temperature
10-second fallback to Virtual Mode if hardware disconnects
Thread-safe - never crashes app
"""

import serial
import serial.tools.list_ports
import threading
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SensorListener:

    ESP32_KEYWORDS = ['CP210', 'CH340', 'FTDI', 'USB Serial', 'ESP32',
                      'Silicon Labs', 'wch', 'USB-SERIAL']

    def __init__(self, baud_rate=115200, timeout=1):
        self.baud_rate        = baud_rate
        self.timeout          = timeout
        self.serial_conn      = None
        self.is_connected     = False
        self.is_running       = False
        self.hardware_timeout = 10

        self.latest_data = {
            'heart_rate':  None,
            'gsr':         None,
            'temperature': None,
            'timestamp':   None,
            'is_virtual':  True
        }

        self._lock           = threading.Lock()
        self._last_data_time = None

    def detect_esp32_port(self):
        """Scan all COM ports for ESP32 USB chip signatures"""
        ports = serial.tools.list_ports.comports()
        for port in ports:
            desc = str(port.description).upper()
            for kw in self.ESP32_KEYWORDS:
                if kw.upper() in desc:
                    logger.info(f'[Sensor] ESP32 found: {port.device} ({port.description})')
                    return port.device
        if ports:
            logger.warning(f'[Sensor] No ESP32 signature found. Trying: {ports[0].device}')
            return ports[0].device
        logger.warning('[Sensor] No COM ports detected.')
        return None

    def connect(self, port=None):
        """Try to open serial connection. Silent fail if no hardware."""
        try:
            if port is None:
                port = self.detect_esp32_port()
            if port is None:
                self.is_connected = False
                return False
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
            self.serial_conn  = serial.Serial(
                port=port, baudrate=self.baud_rate, timeout=self.timeout
            )
            self.is_connected = True
            logger.info(f'[Sensor] Connected to {port} @ {self.baud_rate} baud')
            return True
        except serial.SerialException as e:
            logger.warning(f'[Sensor] Connect failed: {e}')
            self.is_connected = False
            return False

    def parse_data(self, raw_line):
        """
        Parse ESP32 format: heart_rate,gsr,temperature
        Example: 82,540,36.4
        Returns dict or None on bad data.
        """
        try:
            raw_line = raw_line.strip()
            if not raw_line:
                return None
            parts = raw_line.split(',')
            if len(parts) != 3:
                return None

            hr   = float(parts[0].strip())
            gsr  = float(parts[1].strip())
            temp = float(parts[2].strip())

            if not (30  <= hr   <= 220): return None
            if not (0   <= gsr  <= 2000): return None
            if not (30  <= temp <= 42):   return None

            return {
                'heart_rate':  int(hr),
                'gsr':         round(gsr,  2),
                'temperature': round(temp, 1),
                'timestamp':   datetime.now().strftime('%H:%M:%S'),
                'is_virtual':  False
            }
        except (ValueError, IndexError):
            return None

    def _listen_loop(self):
        while self.is_running:
            try:
                if self.serial_conn and self.serial_conn.is_open:
                    raw = self.serial_conn.readline().decode('utf-8', errors='ignore')
                    if raw.strip():
                        parsed = self.parse_data(raw)
                        if parsed:
                            with self._lock:
                                self.latest_data     = parsed
                                self._last_data_time = time.time()
                else:
                    time.sleep(2)
                    self.connect()
            except serial.SerialException as e:
                logger.warning(f'[Sensor] Read error: {e}')
                self.is_connected = False
                time.sleep(3)
                self.connect()
            except Exception as e:
                logger.error(f'[Sensor] Unexpected error: {e}')
                time.sleep(1)
            time.sleep(0.05)

    def start_listening(self):
        """Start background sensor thread. Safe to call multiple times."""
        self.connect()
        self.is_running = True
        t = threading.Thread(
            target=self._listen_loop,
            daemon=True,
            name='SensorListenerThread'
        )
        t.start()
        logger.info('[Sensor] Listener thread started.')

    def stop_listening(self):
        self.is_running = False
        try:
            if self.serial_conn:
                self.serial_conn.close()
        except Exception:
            pass

    def get_latest_data(self):
        with self._lock:
            return self.latest_data.copy()

    def is_hardware_active(self):
        """Returns True if data received within hardware_timeout window"""
        if self._last_data_time is None:
            return False
        return (time.time() - self._last_data_time) < self.hardware_timeout

    def get_virtual_estimates(self, stress_level=5, activity=3):
        """Generate realistic virtual sensor values when ESP32 not connected"""
        hr   = int(max(60, min(110, 72 + stress_level * 2 + activity * 1.5)))
        gsr  = round(2.0 + stress_level * 0.8, 2)
        temp = round(36.5 + (stress_level - 5) * 0.04, 1)
        return {
            'heart_rate':  hr,
            'gsr':         gsr,
            'temperature': temp,
            'timestamp':   datetime.now().strftime('%H:%M:%S'),
            'is_virtual':  True
        }
