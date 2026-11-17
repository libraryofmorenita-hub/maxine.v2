from blood_pressure import parse
from sensor_manager import Window

def test_cuff_parse():
    assert parse("SYS:128,DIA:82,PUL:66\r\n") == (128, 82, 66)
    assert parse("SYS:40,DIA:20") is None          # impossible
    assert parse("SYS:120,DIA:130") is None        # diastolic above systolic
    assert parse("garbage") is None

def test_window_ring_order():
    w = Window(fs=1, seconds=3)
    for v in (1, 2, 3, 4, 5):
        w.push(v)
    assert w.full() and w.values() == [3, 4, 5]
