"""
UART blood pressure module.

Oscillometric modules differ in their output format, and the validated cuffs
on the v2 list (A&D UA-651BLE, SunTech) speak their own protocols, so this
parser is written against a simple text line, e.g.  SYS:128,DIA:82,PUL:66
Adapt parse() to the module you buy; the rest of the bedside code only
needs (sbp, dbp, pulse).
"""


def parse(line):
    try:
        parts = dict(p.split(":") for p in line.strip().split(","))
        sbp, dbp = int(parts["SYS"]), int(parts["DIA"])
        pul = int(parts.get("PUL", 0)) or None
    except (ValueError, KeyError):
        return None
    if not (60 <= sbp <= 260 and 30 <= dbp <= 160 and dbp < sbp):
        return None  # reject impossible readings rather than alert on them
    return sbp, dbp, pul


class Cuff:
    START = b"START\r\n"

    def __init__(self, uart):
        self.uart = uart

    def start(self):
        self.uart.write(self.START)

    def poll(self):
        line = self.uart.readline()
        return parse(line.decode()) if line else None
