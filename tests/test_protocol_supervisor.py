import pytest, ble_protocol as p
from supervisor import Supervisor

def test_roundtrip():
    pkt = p.encode(7, hr=64.3, spo2=97.1, temp_c=33.42, resp=14.0, motion_g=0.03, battery=88)
    assert len(pkt) == 16
    d = p.decode(pkt)
    assert d["hr"] == 64.3 and d["temp_c"] == 33.42 and d["battery"] == 88 and d["seq"] == 7

def test_missing_values_are_none_not_zero():
    d = p.decode(p.encode(1))
    assert d["hr"] is None and d["temp_c"] is None

def test_negative_temp_and_crc():
    pkt = bytearray(p.encode(2, temp_c=-1.5))
    assert p.decode(bytes(pkt))["temp_c"] == -1.5
    pkt[4] ^= 1
    with pytest.raises(ValueError):
        p.decode(bytes(pkt))

def test_dropped_wraps():
    assert p.dropped(65534, 1) == 2 and p.dropped(None, 5) == 0

def test_supervisor_faults():
    s = Supervisor()
    assert not s.healthy(0)
    for ch in ("heart_rate", "temperature", "respiration", "link"):
        s.mark(ch, 0)
    assert s.healthy(5)
    assert ("heart_rate", "no good reading for 20 s") in s.faults(20)
    s.mark("heart_rate", 20); s.mark("link", 20); s.set_battery(10)
    assert any(c == "battery" for c, _ in s.faults(21))
