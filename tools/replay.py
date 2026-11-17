"""
replay.py: run the real MAXINE alert logic over a simulated night.

    python tools/replay.py ad_episode          # prints the timeline
    python tools/replay.py ad_episode --plot   # also writes replay_ad_episode.png

Scenarios: normal_night, ad_episode, sensor_dropout. The signals are
synthetic stand-ins, shaped from published AD physiology, so the logic can
be exercised before there is bench data. Swap in a CSV of real readings
(t, hr, temp_c, sbp) with --csv when there is.
"""
import argparse, csv, math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "firmware", "shared"))
from ad_monitor import ADMonitor  # noqa: E402
from supervisor import Supervisor  # noqa: E402

STEP = 5  # seconds between wearable readings


def truth(scenario, t, rnd):
    """True heart rate, skin temp and systolic at time t (seconds)."""
    hr, temp, sbp = 72.0, 33.2, 112.0
    if scenario == "ad_episode" and t >= 3600:
        k = min(1.0, (t - 3600) / 600.0)            # builds over 10 minutes
        if t >= 5400:                                 # trigger removed at 90 min
            k = max(0.0, k - (t - 5400) / 900.0)
        hr -= 20 * k; temp += 0.8 * k; sbp += 55 * k
    noise = (rnd.gauss(0, 1.5), rnd.gauss(0, 0.05), rnd.gauss(0, 3))
    hr, temp, sbp = hr + noise[0], temp + noise[1], sbp + noise[2]
    if scenario == "sensor_dropout" and 2400 <= t < 2700:
        hr = None
    return hr, temp, sbp


def simulate(scenario, minutes=150, seed=7):
    rnd = random.Random(seed)
    mon, sup = ADMonitor(baseline_hr=72), Supervisor()
    rows, faults_seen = [], set()
    for t in range(0, minutes * 60, STEP):
        hr, temp, sbp = truth(scenario, t, rnd)
        mon.on_heart_rate(t, hr); mon.on_temperature(t, temp)
        for ch in ("temperature", "respiration", "link"):
            sup.mark(ch, t)
        if hr is not None:
            sup.mark("heart_rate", t)
        cuff = None
        if mon.wants_cuff(t):
            cuff = round(sbp)
            mon.on_cuff(t, cuff)
        for ch, why in sup.faults(t):
            if ch not in faults_seen:
                faults_seen.add(ch); mon.events.append((t, "fault", "%s: %s" % (ch, why)))
        for ch in list(faults_seen):
            if ch not in [c for c, _ in sup.faults(t)]:
                faults_seen.discard(ch); mon.events.append((t, "fault_cleared", ch))
        rows.append((t, hr, temp, sbp, cuff, mon.state))
    return rows, mon


def report(rows, mon):
    def hm(t): return "%d:%02d" % (t // 3600, (t % 3600) // 60)
    for t, kind, detail in sorted(mon.events, key=lambda e: e[0]):
        print("%6s  %-14s %s" % (hm(t), kind, detail))
    cuffs = [r for r in rows if r[4] is not None]
    alert = [r for r in rows if r[5] in ("ad", "significant")]
    print("\ncuff readings: %d   time in alert: %d min" % (len(cuffs), len(alert) * STEP // 60))


def plot(rows, mon, path):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    m = [r[0] / 60 for r in rows]
    fig, ax = plt.subplots(3, 1, figsize=(10, 7), sharex=True)
    ax[0].plot(m, [r[1] if r[1] is not None else float("nan") for r in rows], lw=.8, color="#7a3b69")
    ax[0].set_ylabel("heart rate (bpm)")
    ax[1].plot(m, [r[2] for r in rows], lw=.8, color="#c07a2c"); ax[1].set_ylabel("skin temp (°C)")
    ax[2].plot(m, [r[3] for r in rows], lw=.6, color="#bbb", label="true systolic")
    cm = [(r[0] / 60, r[4]) for r in rows if r[4] is not None]
    ax[2].scatter([c[0] for c in cm], [c[1] for c in cm], s=14, color="#1f4e79", zorder=3, label="cuff")
    if mon.baseline_sbp:
        ax[2].axhline(mon.baseline_sbp + 20, ls="--", lw=.8, color="#b22", label="alert line (+20)")
    ax[2].set_ylabel("systolic (mmHg)"); ax[2].set_xlabel("minutes"); ax[2].legend(loc="upper left", fontsize=8)
    for a in ax:
        for i, r in enumerate(rows):
            if r[5] in ("ad", "significant") and (i == 0 or rows[i-1][5] not in ("ad", "significant")):
                start = r[0] / 60
            if r[5] in ("ad", "significant") and (i == len(rows)-1 or rows[i+1][5] not in ("ad", "significant")):
                a.axvspan(start, r[0] / 60, color="#f3c6c6", alpha=.5, lw=0)
    fig.suptitle("MAXINE replay (synthetic, research only)")
    fig.tight_layout(); fig.savefig(path, dpi=130)
    print("wrote", path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario", choices=["normal_night", "ad_episode", "sensor_dropout"])
    ap.add_argument("--plot", action="store_true")
    a = ap.parse_args()
    rows, mon = simulate(a.scenario)
    report(rows, mon)
    if a.plot:
        plot(rows, mon, "replay_%s.png" % a.scenario)
