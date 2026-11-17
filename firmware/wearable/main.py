"""
Wearable unit: sample, compute vitals every 5 s, send one BLE packet.
Research prototype. Bench-untested; pin numbers match docs/WIRING.md.
"""
import sys
sys.path.append("/shared")

from machine import I2C, Pin, ADC
from base import asyncio
import vitals, ble_protocol
from sensor_manager import SensorManager
from sensors.max30102 import MAX30102
from sensors.motion import MPU6050
from sensors import temperature
from ble_peripheral import VitalsPeripheral

i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
pulse, imu = MAX30102(i2c), MPU6050(i2c)
battery_adc = ADC(Pin(35))
sm = SensorManager()
sm.add("ir", pulse.fs, 10)
sm.add("chest", 25, 30)
sm.add("mag", 25, 5)
ble = VitalsPeripheral("MAXINE-W")


def battery_pct():
    v = battery_adc.read() / 4095 * 3.3 * 2   # 1:1 divider
    return max(0, min(100, int((v - 3.3) / (4.2 - 3.3) * 100)))


async def sample():
    while True:
        for _, ir in pulse.read():
            sm.push("ir", ir)
        x, y, z = imu.accel()
        sm.push("chest", z)
        sm.push("mag", (x * x + y * y + z * z) ** 0.5)
        await asyncio.sleep_ms(40)


async def report():
    seq = 0
    while True:
        await asyncio.sleep(5)
        motion = vitals.motion_level(sm.get("mag"), 25)
        flags = ble_protocol.FLAG_MOTION if motion > 0.05 else 0
        hr = None if flags else vitals.heart_rate(sm.get("ir"), pulse.fs)
        try:
            t = temperature.read_c(i2c)
        except OSError:
            t, flags = None, flags | ble_protocol.FLAG_FAULT
        bat = battery_pct()
        if bat <= 15:
            flags |= ble_protocol.FLAG_LOW_BATTERY
        ble.send(ble_protocol.encode(seq, hr=hr, temp_c=t,
                 resp=vitals.respiration_rate(sm.get("chest"), 25),
                 motion_g=motion, battery=bat, flags=flags))
        seq += 1


async def run():
    await asyncio.gather(sample(), report())

asyncio.run(run())
