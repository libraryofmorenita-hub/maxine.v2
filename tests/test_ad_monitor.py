import ad_monitor as m

def learned(sbp=110, hr=70):
    a = m.ADMonitor(baseline_sbp=sbp, baseline_hr=hr)
    return a

def test_learns_baseline_from_cuff():
    a = m.ADMonitor()
    assert a.wants_cuff(0)
    for i, s in enumerate((108, 112, 110)):
        a.on_cuff(i * 100, s)
    assert a.baseline_sbp == 110

def test_hr_drop_requests_cuff_but_does_not_alert():
    a = learned()
    a.on_heart_rate(10, 55)
    assert a.state == m.WATCH and a.wants_cuff(10) and not a.alerting

def test_ad_and_significant_thresholds():
    a = learned()
    a.on_cuff(0, 129); assert a.state == m.NORMAL
    a.on_cuff(200, 130); assert a.state == m.AD and a.alerting
    a.on_cuff(400, 151); assert a.state == m.SIGNIFICANT
    b = learned(sbp=95); b.on_cuff(0, 136); assert b.state == m.SIGNIFICANT  # > +40

def test_rechecks_every_two_minutes_while_elevated():
    a = learned(); a.on_cuff(0, 140)
    assert not a.wants_cuff(60)
    assert a.wants_cuff(120)

def test_cuff_gap_protects_the_arm():
    a = learned(); a.on_cuff(0, 112); a.on_heart_rate(30, 50)
    assert a.state == m.WATCH and not a.wants_cuff(30) and a.wants_cuff(95)

def test_temperature_rise_suspects():
    a = learned()
    for t in range(0, 240, 10):
        a.on_temperature(t, 33.0 + t / 400.0)
    assert a.state == m.WATCH

def test_returns_to_normal():
    a = learned(); a.on_cuff(0, 140); a.on_cuff(200, 115)
    assert a.state == m.NORMAL and not a.alerting
