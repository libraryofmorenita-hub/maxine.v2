"""
ad_monitor.py: the autonomic dysreflexia (AD) watch, cuff in the loop.

Research software, not a medical device. It is built to be studied under an
IRB, never to replace clinical judgment or standard care.

How it works
    The chest unit sends heart rate and skin temperature continuously. The
    monitor learns the person's own resting baseline, and when the pattern
    that often precedes AD appears (heart rate falling well below baseline,
    or a quick rise in skin temperature) it asks the bedside cuff for a
    blood pressure reading. The cuff is the ground truth: only a measured
    systolic pressure can raise an alert.

Thresholds come from published guidance (Can-SCIP; StatPearls):
    AD                 systolic >= baseline + 20 mmHg (adults)
    significant AD     systolic >= 150 mmHg, or more than baseline + 40
    while elevated     re-measure every 2 minutes until it settles
The suspicion thresholds (heart rate drop, temperature rise) are starting
points to be tuned on study data, and are named constants for that reason.
"""

NORMAL = "normal"
WATCH = "watch"            # suspicious pattern, cuff requested
AD = "ad"                  # measured systolic >= baseline + 20
SIGNIFICANT = "significant"  # measured systolic >= 150 or > baseline + 40

# Tunable starting points (see module docstring).
SBP_RISE_AD = 20
SBP_RISE_SIGNIFICANT = 40
SBP_SIGNIFICANT = 150
HR_DROP_SUSPECT = 12        # bpm below baseline heart rate
TEMP_RISE_SUSPECT = 0.4     # deg C rise within the trend window
TREND_WINDOW_S = 300        # look back 5 minutes for the temperature rise
RECHECK_S = 120             # cuff every 2 minutes while elevated
MIN_CUFF_GAP_S = 90         # never inflate more often than this
BASELINE_READINGS = 3       # resting cuff readings that set the baseline


class ADMonitor:
    def __init__(self, baseline_sbp=None, baseline_hr=None):
        self.baseline_sbp = baseline_sbp
        self.baseline_hr = baseline_hr
        self._sbp_seed = []
        self._hr_seed = []
        self._temps = []          # (t, celsius)
        self.state = NORMAL
        self.last_cuff_t = None
        self.last_sbp = None
        self.events = []          # (t, kind, detail) for the log and replay

    # ── inputs ────────────────────────────────────────────────────────
    def on_heart_rate(self, t, bpm):
        if bpm is None:
            return
        if self.baseline_hr is None:
            self._hr_seed.append(bpm)
            if len(self._hr_seed) >= 30:  # ~30 readings of rest
                self.baseline_hr = sorted(self._hr_seed)[len(self._hr_seed) // 2]
                self._log(t, "baseline_hr", round(self.baseline_hr, 1))
            return
        if self.state == NORMAL and bpm <= self.baseline_hr - HR_DROP_SUSPECT:
            self._suspect(t, "heart rate %d below baseline %d" % (bpm, self.baseline_hr))

    def on_temperature(self, t, celsius):
        if celsius is None:
            return
        self._temps.append((t, celsius))
        while self._temps and t - self._temps[0][0] > TREND_WINDOW_S:
            self._temps.pop(0)
        low = min(c for _, c in self._temps)
        if self.state == NORMAL and celsius - low >= TEMP_RISE_SUSPECT:
            self._suspect(t, "skin temperature up %.1f C in %d min" % (celsius - low, TREND_WINDOW_S // 60))

    def on_cuff(self, t, sbp, dbp=None):
        """A measured blood pressure. The only input that can raise an alert."""
        self.last_cuff_t = t
        self.last_sbp = sbp
        if self.baseline_sbp is None:
            self._sbp_seed.append(sbp)
            if len(self._sbp_seed) >= BASELINE_READINGS:
                self.baseline_sbp = sorted(self._sbp_seed)[len(self._sbp_seed) // 2]
                self._log(t, "baseline_sbp", self.baseline_sbp)
            return
        rise = sbp - self.baseline_sbp
        if sbp >= SBP_SIGNIFICANT or rise > SBP_RISE_SIGNIFICANT:
            new = SIGNIFICANT
        elif rise >= SBP_RISE_AD:
            new = AD
        else:
            new = NORMAL
        if new != self.state:
            self._log(t, new, "systolic %d (baseline %d, +%d)" % (sbp, self.baseline_sbp, rise))
        self.state = new

    # ── outputs ───────────────────────────────────────────────────────
    def wants_cuff(self, t):
        """Should the bedside unit take a blood pressure now?"""
        if self.last_cuff_t is not None and t - self.last_cuff_t < MIN_CUFF_GAP_S:
            return False
        if self.baseline_sbp is None:
            return True  # still learning the baseline
        if self.state in (WATCH,):
            return True
        if self.state in (AD, SIGNIFICANT):
            return self.last_cuff_t is None or t - self.last_cuff_t >= RECHECK_S
        return False

    @property
    def alerting(self):
        return self.state in (AD, SIGNIFICANT)

    # ── internals ─────────────────────────────────────────────────────
    def _suspect(self, t, why):
        if self.baseline_sbp is None:
            return
        self.state = WATCH
        self._log(t, WATCH, why)

    def _log(self, t, kind, detail):
        self.events.append((t, kind, detail))
