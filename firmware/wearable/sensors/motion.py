"""MPU-6050 IMU (I2C 0x68). Acceleration in g, for respiration and motion."""

ADDR = 0x68


class MPU6050:
    def __init__(self, i2c):
        self.i2c = i2c
        i2c.writeto_mem(ADDR, 0x6B, b"\x00")  # wake
        i2c.writeto_mem(ADDR, 0x1C, b"\x00")  # +/-2 g
        i2c.writeto_mem(ADDR, 0x1A, b"\x05")  # 10 Hz low-pass

    def accel(self):
        d = self.i2c.readfrom_mem(ADDR, 0x3B, 6)
        def s16(h, l):
            v = (h << 8) | l
            return v - 65536 if v & 0x8000 else v
        return (s16(d[0], d[1]) / 16384.0, s16(d[2], d[3]) / 16384.0, s16(d[4], d[5]) / 16384.0)
