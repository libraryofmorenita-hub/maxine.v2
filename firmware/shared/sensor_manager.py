"""
sensor_manager.py: rolling sample windows, one per channel.

Drivers push raw samples in; the main loop asks for a window (the last N
seconds) to hand to vitals.py. Fixed-size buffers so memory never grows on
the device.
"""

class Window:
    def __init__(self, fs, seconds):
        self.fs = fs
        self.size = int(fs * seconds)
        self.buf = [0.0] * self.size
        self.i = 0
        self.count = 0

    def push(self, v):
        self.buf[self.i] = v
        self.i = (self.i + 1) % self.size
        if self.count < self.size:
            self.count += 1

    def full(self):
        return self.count == self.size

    def values(self):
        if self.count < self.size:
            return self.buf[: self.count]
        return self.buf[self.i:] + self.buf[: self.i]


class SensorManager:
    def __init__(self):
        self.windows = {}

    def add(self, name, fs, seconds):
        self.windows[name] = Window(fs, seconds)
        return self.windows[name]

    def push(self, name, v):
        self.windows[name].push(v)

    def get(self, name):
        return self.windows[name].values()
