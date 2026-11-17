"""
Display adapter for the Waveshare 4.2" e-paper, using mcauser's
micropython-waveshare-epaper driver (epaper4in2.py, uploaded separately).
If the driver or panel is missing, it prints to the serial console instead,
so the bedside logic still runs on a bare board.
"""

W, H = 400, 300


def fmt(v, unit, nd=0):
    return "--" if v is None else ("%." + str(nd) + "f%s") % (v, unit)


class Screen:
    def __init__(self):
        self.epd = None
        self.last = None
        try:
            import epaper4in2, framebuf
            from machine import SPI, Pin
            spi = SPI(2, baudrate=2000000, sck=Pin(18), mosi=Pin(23))
            self.epd = epaper4in2.EPD(spi, Pin(5), Pin(17), Pin(16), Pin(4))
            self.epd.init()
            self.buf = bytearray(W * H // 8)
            self.fb = framebuf.FrameBuffer(self.buf, W, H, framebuf.MONO_HLSB)
        except (ImportError, OSError):
            self.epd = None

    def show(self, d, state, faults):
        lines = [
            "HR   " + fmt(d.get("hr"), " bpm"),
            "BP   " + ("--" if d.get("sbp") is None else "%d/%d" % (d["sbp"], d["dbp"])),
            "TEMP " + fmt(d.get("temp_c"), " C", 1),
            "RESP " + fmt(d.get("resp"), " /min"),
            "",
            "STATE: " + state.upper(),
        ] + ["! " + ch + ": " + why for ch, why in faults]
        if lines == self.last:
            return  # e-paper refresh is slow and wears the panel
        self.last = lines
        if self.epd is None:
            print("\n".join(lines))
            return
        self.fb.fill(1)
        for i, line in enumerate(lines[:14]):
            self.fb.text(line, 12, 12 + i * 20, 0)
        self.epd.display_frame(self.buf)
