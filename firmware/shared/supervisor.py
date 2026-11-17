"""
supervisor.py: an independent safety check that watches the watcher.

Each sensor channel reports when it last produced a trustworthy value. If a
channel goes quiet for too long, the battery runs low, or the link to the
other unit drops, the supervisor raises a fault that the display and the
caregiver alert show plainly. A silent monitor must never look like a
calm patient.
"""

# Seconds a channel may go without a good value before it is a fault.
DEFAULT_TIMEOUTS = {
    "heart_rate": 15,
    "temperature": 60,
    "respiration": 60,
    "link": 10,
}
LOW_BATTERY = 15  # percent


class Supervisor:
    def __init__(self, timeouts=None):
        self.timeouts = dict(DEFAULT_TIMEOUTS)
        if timeouts:
            self.timeouts.update(timeouts)
        self.last_good = {}
        self.battery = None

    def mark(self, channel, t):
        """Call whenever a channel produces a value it trusts."""
        self.last_good[channel] = t

    def set_battery(self, percent):
        self.battery = percent

    def faults(self, t):
        out = []
        for ch, limit in self.timeouts.items():
            last = self.last_good.get(ch)
            if last is None:
                out.append((ch, "no data yet"))
            elif t - last > limit:
                out.append((ch, "no good reading for %d s" % (t - last)))
        if self.battery is not None and self.battery <= LOW_BATTERY:
            out.append(("battery", "battery at %d%%" % self.battery))
        return out

    def healthy(self, t):
        return not self.faults(t)
