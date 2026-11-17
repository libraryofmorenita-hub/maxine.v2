"""
Bedside unit: receives wearable packets, runs the AD monitor and the
supervisor, drives the cuff, the display and the alarm.
Research prototype. Bench-untested.
"""
import sys
sys.path.append("/shared")

from machine import UART, Pin
from base import asyncio, now_s
import ble_protocol
from ad_monitor import ADMonitor
from supervisor import Supervisor
from blood_pressure import Cuff
from ble.ble_central import VitalsCentral
from display.epaper import Screen

mon, sup = ADMonitor(), Supervisor()
cuff = Cuff(UART(2, 9600, tx=27, rx=26))
buzzer = Pin(25, Pin.OUT)
screen = Screen()
latest = {}
prev_seq = [None]


def on_packet(raw):
    try:
        d = ble_protocol.decode(raw)
    except ValueError:
        return
    t = now_s()
    sup.mark("link", t)
    lost = ble_protocol.dropped(prev_seq[0], d["seq"])
    prev_seq[0] = d["seq"]
    if d["hr"] is not None:
        sup.mark("heart_rate", t)
    if d["temp_c"] is not None:
        sup.mark("temperature", t)
    if d["resp"] is not None:
        sup.mark("respiration", t)
    sup.set_battery(d["battery"])
    mon.on_heart_rate(t, d["hr"])
    mon.on_temperature(t, d["temp_c"])
    latest.update(d, lost=lost)


async def cuff_loop():
    measuring = False
    while True:
        t = now_s()
        if not measuring and mon.wants_cuff(t):
            cuff.start()
            measuring = True
        if measuring:
            r = cuff.poll()
            if r:
                mon.on_cuff(t, r[0], r[1])
                latest["sbp"], latest["dbp"] = r[0], r[1]
                measuring = False
        await asyncio.sleep_ms(200)


async def alarm_loop():
    while True:
        t = now_s()
        loud = mon.alerting or not sup.healthy(t)
        buzzer.value(1 if loud else 0)
        screen.show(latest, mon.state, sup.faults(t))
        await asyncio.sleep(2)


async def run():
    VitalsCentral("MAXINE-W", on_packet).start()
    await asyncio.gather(cuff_loop(), alarm_loop())

asyncio.run(run())
