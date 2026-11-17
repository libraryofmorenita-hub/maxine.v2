"""
vitals.py: turning raw sensor samples into vital signs.

Written in the subset of Python that runs on both MicroPython (on the ESP32)
and desktop CPython (for tests and replay), so the exact code that ships on
the device is the code we test. No numpy, no f-string-only tricks, plain
lists in and plain numbers out.

Every function returns None when it can't give a trustworthy number. A
monitor that says "I don't know" is safer than one that guesses.
"""

# ── small helpers ───────────────────────────────────────────────────────

def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def median(xs):
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def moving_average(xs, width):
    """Centered moving average; the edges use whatever window fits."""
    if width <= 1 or len(xs) < 2:
        return list(xs)
    half = width // 2
    out = []
    run = 0.0
    # prefix sums keep this O(n), which matters on a microcontroller
    pre = [0.0]
    for x in xs:
        run += x
        pre.append(run)
    n = len(xs)
    for i in range(n):
        a = max(0, i - half)
        b = min(n, i + half + 1)
        out.append((pre[b] - pre[a]) / (b - a))
    return out


def detrend(xs, fs, window_s=0.75):
    """Remove slow baseline drift (breathing, posture) from a pulse signal."""
    base = moving_average(xs, max(3, int(fs * window_s)))
    return [x - b for x, b in zip(xs, base)]


# ── heart rate from a pulse (PPG) or ECG waveform ───────────────────────

def find_beats(xs, fs, min_bpm=30, max_bpm=200):
    """Indices of heartbeats in a waveform.

    Smooth lightly, remove drift, then take local maxima above an adaptive
    threshold, never closer together than the fastest plausible heart rate
    allows (the refractory period)."""
    if len(xs) < fs * 2:
        return []
    sig = detrend(moving_average(xs, max(1, int(fs * 0.05))), fs)
    peak = max(sig)
    trough = min(sig)
    if peak - trough <= 1e-9:
        return []  # flat line: sensor off or saturated
    threshold = trough + 0.55 * (peak - trough)
    refractory = int(fs * 60.0 / max_bpm)
    beats = []
    for i in range(1, len(sig) - 1):
        if sig[i] >= threshold and sig[i] >= sig[i - 1] and sig[i] > sig[i + 1]:
            if beats and i - beats[-1] < refractory:
                if sig[i] > sig[beats[-1]]:
                    beats[-1] = i  # keep the taller of two close peaks
                continue
            beats.append(i)
    return beats


def rr_intervals_ms(beats, fs):
    return [(b - a) * 1000.0 / fs for a, b in zip(beats, beats[1:])]


def heart_rate(xs, fs, min_bpm=30, max_bpm=200):
    """Beats per minute from the median beat-to-beat interval, or None.

    The median ignores the odd missed or doubled beat; we also refuse to
    answer when intervals disagree too much (motion artifact)."""
    rr = rr_intervals_ms(find_beats(xs, fs, min_bpm, max_bpm), fs)
    if len(rr) < 3:
        return None
    m = median(rr)
    good = [r for r in rr if abs(r - m) < 0.25 * m]
    if len(good) < 0.6 * len(rr):
        return None
    bpm = 60000.0 / median(good)
    return bpm if min_bpm <= bpm <= max_bpm else None


def rmssd(rr_ms):
    """Heart rate variability: root mean square of successive differences."""
    if len(rr_ms) < 3:
        return None
    diffs = [(b - a) ** 2 for a, b in zip(rr_ms, rr_ms[1:])]
    return (sum(diffs) / len(diffs)) ** 0.5


# ── respiration from chest motion ───────────────────────────────────────

def respiration_rate(accel, fs, min_brpm=4, max_brpm=40):
    """Breaths per minute from chest-wall acceleration, or None.

    Breathing moves the chest slowly (0.1 to 0.6 Hz). Smooth away the
    heartbeat and jitter, then count upward zero crossings."""
    if len(accel) < fs * 15:
        return None  # need at least ~15 s for a stable count
    smooth = moving_average(accel, max(3, int(fs * 1.0)))
    centered = detrend(smooth, fs, window_s=8.0)
    amp = max(centered) - min(centered)
    if amp <= 1e-6:
        return None
    hyst = 0.1 * amp  # ignore wiggles smaller than 10% of a breath
    crossings = []
    armed = False
    for i, v in enumerate(centered):
        if v < -hyst:
            armed = True
        elif v > hyst and armed:
            crossings.append(i)
            armed = False
    if len(crossings) < 3:
        return None
    period_s = median([(b - a) / fs for a, b in zip(crossings, crossings[1:])])
    brpm = 60.0 / period_s
    return brpm if min_brpm <= brpm <= max_brpm else None


# ── signal quality ──────────────────────────────────────────────────────

def motion_level(accel_mag, fs):
    """Standard deviation of acceleration magnitude over the window (in g).
    Above ~0.05 g most optical and ECG readings should be distrusted."""
    if len(accel_mag) < 2:
        return 0.0
    m = mean(accel_mag)
    return (sum((a - m) ** 2 for a in accel_mag) / (len(accel_mag) - 1)) ** 0.5
