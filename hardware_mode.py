"""
Hardware Mode Manager
Auto-switches between VIRTUAL and PHYSICAL biosensor modes.
Monitors hardware heartbeat every second.
"""

import threading
import time
import logging
from sensor_listener import SensorListener

logger = logging.getLogger(__name__)


class HardwareModeManager:

    VIRTUAL  = 'VIRTUAL'
    PHYSICAL = 'PHYSICAL'

    def __init__(self, sensor_listener: SensorListener):
        self.sensor_listener = sensor_listener
        self._mode           = self.VIRTUAL
        self._lock           = threading.Lock()
        self._start_watcher()

    def _start_watcher(self):
        t = threading.Thread(
            target=self._watch_loop, daemon=True, name='ModeWatcher'
        )
        t.start()

    def _watch_loop(self):
        while True:
            try:
                new_mode = (
                    self.PHYSICAL
                    if self.sensor_listener.is_hardware_active()
                    else self.VIRTUAL
                )
                with self._lock:
                    if self._mode != new_mode:
                        logger.info(f'[Mode] Switched to {new_mode}')
                        self._mode = new_mode
            except Exception as e:
                logger.error(f'[Mode] Watcher error: {e}')
            time.sleep(1)

    def get_current_mode(self):
        with self._lock:
            return self._mode

    def is_physical_mode(self):
        return self.get_current_mode() == self.PHYSICAL

    def is_virtual_mode(self):
        return self.get_current_mode() == self.VIRTUAL

    def get_sensor_data(self, stress_level=5, activity=3):
        """
        Returns real data in PHYSICAL mode, virtual estimates in VIRTUAL mode.
        Always returns same dict structure - guaranteed safe for ML model.
        """
        if self.is_physical_mode():
            data = self.sensor_listener.get_latest_data()
            if data and data.get('heart_rate') is not None:
                data['is_virtual'] = False
                return data
        return self.sensor_listener.get_virtual_estimates(stress_level, activity)

    def get_status(self):
        """Returns (status_string, live_data_or_None)"""
        mode   = self.get_current_mode()
        data   = None
        status = 'ONLINE' if mode == self.PHYSICAL else 'OFFLINE'
        if mode == self.PHYSICAL:
            latest = self.sensor_listener.get_latest_data()
            if latest and latest.get('heart_rate') is not None:
                data = latest
        return status, data
