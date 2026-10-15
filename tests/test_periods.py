import pytest
from datetime import date
from meridian.store.periods import parse_period

def test_period_parsing():
    ref = date(2026, 9, 28)

    # 1. last_7_days
    w7 = parse_period("last_7_days", ref_date=ref)
    assert w7.start == "2026-09-21"
    assert w7.end_exclusive == "2026-09-28"

    # 2. last_30_days
    w30 = parse_period("last_30_days", ref_date=ref)
    assert w30.start == "2026-08-29"
    assert w30.end_exclusive == "2026-09-28"

    # 3. ISO Week 2026-W36
    w36 = parse_period("2026-W36", ref_date=ref)
    assert w36.start == "2026-08-31" # Monday
    assert w36.end_exclusive == "2026-09-07" # Next Monday

    # 4. Month 2026-09
    m09 = parse_period("2026-09", ref_date=ref)
    assert m09.start == "2026-09-01"
    assert m09.end_exclusive == "2026-10-01"

    # 5. Invalid period
    with pytest.raises(ValueError):
        parse_period("last_week")

    with pytest.raises(ValueError):
        parse_period("2026-W99")
