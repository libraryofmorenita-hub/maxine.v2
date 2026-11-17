import vitals
from synth import ppg, chest

def test_heart_rate_tracks_true_rate():
    for bpm in (48, 62, 75, 110):
        hr = vitals.heart_rate(ppg(bpm, 10), 50)
        assert hr is not None and abs(hr - bpm) < 3, (bpm, hr)

def test_flat_signal_returns_none():
    assert vitals.heart_rate([0.5] * 500, 50) is None

def test_short_window_returns_none():
    assert vitals.heart_rate(ppg(70, 1), 50) is None

def test_respiration():
    for br in (8, 14, 22):
        r = vitals.respiration_rate(chest(br, 60), 25)
        assert r is not None and abs(r - br) < 1.5, (br, r)

def test_rmssd_and_median():
    assert vitals.rmssd([800, 810, 790, 805]) > 0
    assert vitals.median([3, 1, 2]) == 2
    assert vitals.rmssd([800]) is None
