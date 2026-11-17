"""base.py: the few things that differ between MicroPython and CPython."""
try:
    import utime as _t
    def now_s():
        return _t.ticks_ms() / 1000.0
    def sleep_ms(ms):
        _t.sleep_ms(ms)
    MICROPYTHON = True
except ImportError:
    import time as _t
    def now_s():
        return _t.monotonic()
    def sleep_ms(ms):
        _t.sleep(ms / 1000.0)
    MICROPYTHON = False

try:
    import uasyncio as asyncio  # noqa: F401
except ImportError:
    import asyncio  # noqa: F401
