"""Camera-based heart rate simulation (PPG concept)"""
import numpy as np
import time


class CameraScanner:
    def simulate_scan(self, duration=3):
        """Simulate webcam PPG heart rate detection"""
        time.sleep(min(duration, 3))
        return int(np.clip(np.random.normal(72, 12), 50, 120))
