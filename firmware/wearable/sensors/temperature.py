"""MLX90614 IR thermometer (I2C 0x5A). Object temperature in deg C.
Skin temperature for trend only; it is not core body temperature."""

ADDR = 0x5A
T_OBJ = 0x07


def read_c(i2c):
    d = i2c.readfrom_mem(ADDR, T_OBJ, 3)
    raw = d[0] | (d[1] << 8)
    if raw & 0x8000:
        return None  # error flag set by the sensor
    return raw * 0.02 - 273.15
