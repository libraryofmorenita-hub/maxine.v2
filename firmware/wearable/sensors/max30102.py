"""MAX30102 pulse sensor (I2C 0x57). Reads red + IR samples from the FIFO.
Register map from the Maxim/ADI MAX30102 datasheet. Bench-untested."""

ADDR = 0x57
FIFO_WR, FIFO_OVF, FIFO_RD, FIFO_DATA = 0x04, 0x05, 0x06, 0x07
MODE, SPO2_CFG, LED1, LED2, PART_ID = 0x09, 0x0A, 0x0C, 0x0D, 0xFF


class MAX30102:
    def __init__(self, i2c, led_current=0x24):
        self.i2c = i2c
        if self._r(PART_ID) != 0x15:
            raise OSError("MAX30102 not found")
        self._w(MODE, 0x40)                 # reset
        self._w(0x08, 0x4F)                 # FIFO: 4-sample average, rollover on
        self._w(SPO2_CFG, 0x27)             # 4096 nA range, 100 sps, 18-bit
        self._w(LED1, led_current)
        self._w(LED2, led_current)
        self._w(MODE, 0x03)                 # SpO2 mode (red + IR)
        for reg in (FIFO_WR, FIFO_OVF, FIFO_RD):
            self._w(reg, 0)
        self.fs = 25                        # 100 sps / 4 averaged

    def read(self):
        """All new samples as a list of (red, ir)."""
        n = (self._r(FIFO_WR) - self._r(FIFO_RD)) & 0x1F
        out = []
        for _ in range(n):
            d = self.i2c.readfrom_mem(ADDR, FIFO_DATA, 6)
            red = ((d[0] << 16) | (d[1] << 8) | d[2]) & 0x3FFFF
            ir = ((d[3] << 16) | (d[4] << 8) | d[5]) & 0x3FFFF
            out.append((red, ir))
        return out

    def _r(self, reg):
        return self.i2c.readfrom_mem(ADDR, reg, 1)[0]

    def _w(self, reg, v):
        self.i2c.writeto_mem(ADDR, reg, bytes([v]))
