"""
ble_protocol.py: the 16-byte vitals packet the wearable sends the bedside.

Shared by both units so they can never disagree about the format.

    byte  0     version (1)
    byte  1     flags: bit0 motion artifact, bit1 low battery, bit2 sensor fault
    bytes 2-3   sequence number (wraps at 65535), to spot dropped packets
    bytes 4-5   heart rate, bpm x 10
    bytes 6-7   SpO2, % x 10
    bytes 8-9   skin temperature, deg C x 100 (signed)
    bytes 10-11 respiration, breaths/min x 10
    byte  12    motion level, g x 100 (capped at 255)
    byte  13    battery, %
    bytes 14    reserved
    byte  15    CRC-8 of bytes 0-14

A value the device could not measure is sent as 0xFFFF (0x7FFF for the
signed temperature) and decoded as None, never as a fake zero.
"""

import struct

SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
VITALS_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
COMMAND_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
VERSION = 1
FMT = "<BBHHHhHBBB"  # 15 bytes, CRC appended
MISSING_U = 0xFFFF
MISSING_S = 0x7FFF

FLAG_MOTION = 1
FLAG_LOW_BATTERY = 2
FLAG_FAULT = 4


def crc8(data):
    """CRC-8/ATM (polynomial 0x07)."""
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def _u(v, scale):
    return MISSING_U if v is None else max(0, min(0xFFFE, int(round(v * scale))))


def _s(v, scale):
    return MISSING_S if v is None else max(-0x7FFF, min(0x7FFE, int(round(v * scale))))


def encode(seq, hr=None, spo2=None, temp_c=None, resp=None, motion_g=0.0, battery=100, flags=0):
    body = struct.pack(
        FMT, VERSION, flags, seq & 0xFFFF,
        _u(hr, 10), _u(spo2, 10), _s(temp_c, 100), _u(resp, 10),
        min(255, int(round(motion_g * 100))), max(0, min(100, int(battery))), 0,
    )
    return body + bytes([crc8(body)])


def decode(packet):
    """Returns a dict, or raises ValueError for a corrupt or unknown packet."""
    if len(packet) != 16:
        raise ValueError("expected 16 bytes, got %d" % len(packet))
    body, crc = packet[:15], packet[15]
    if crc8(body) != crc:
        raise ValueError("CRC mismatch")
    ver, flags, seq, hr, spo2, temp, resp, motion, battery, _ = struct.unpack(FMT, body)
    if ver != VERSION:
        raise ValueError("unknown packet version %d" % ver)
    return {
        "seq": seq,
        "flags": flags,
        "hr": None if hr == MISSING_U else hr / 10,
        "spo2": None if spo2 == MISSING_U else spo2 / 10,
        "temp_c": None if temp == MISSING_S else temp / 100,
        "resp": None if resp == MISSING_U else resp / 10,
        "motion_g": motion / 100,
        "battery": battery,
    }


def dropped(prev_seq, seq):
    """How many packets were lost between two sequence numbers."""
    if prev_seq is None:
        return 0
    return (seq - prev_seq - 1) & 0xFFFF
