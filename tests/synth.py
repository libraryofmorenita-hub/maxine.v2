"""Synthetic signals for tests and replay. Deterministic (seeded)."""
import math, random

def ppg(bpm, seconds, fs=50, noise=0.05, seed=1):
    rnd = random.Random(seed)
    out, phase = [], 0.0
    for i in range(int(seconds * fs)):
        phase += bpm / 60.0 / fs
        p = phase % 1.0
        beat = math.exp(-((p - 0.2) ** 2) / 0.004) + 0.3 * math.exp(-((p - 0.45) ** 2) / 0.01)
        drift = 0.4 * math.sin(2 * math.pi * 0.25 * i / fs)
        out.append(beat + drift + rnd.gauss(0, noise))
    return out

def chest(brpm, seconds, fs=25, noise=0.002, seed=2):
    rnd = random.Random(seed)
    return [0.02 * math.sin(2 * math.pi * brpm / 60.0 * i / fs) + rnd.gauss(0, noise)
            for i in range(int(seconds * fs))]
