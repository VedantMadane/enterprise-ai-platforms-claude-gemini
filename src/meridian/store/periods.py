import re
from datetime import date, timedelta
from typing import Tuple
from meridian.config import REFERENCE_DATE
from meridian.models.unified import PeriodWindow

PERIOD_REGEX = re.compile(r"^(last_7_days|last_30_days|(\d{4})-W(\d{2})|(\d{4})-(\d{2}))$")

def parse_period(period_str: str, ref_date: date = REFERENCE_DATE) -> PeriodWindow:
    """
    Parses a period string into an inclusive start date and exclusive end date (ISO format string).
    
    Supported formats:
      - 'last_7_days': 7 days ending at ref_date [ref_date - 7 days, ref_date)
      - 'last_30_days': 30 days ending at ref_date [ref_date - 30 days, ref_date)
      - 'YYYY-Www' (e.g., '2026-W36'): ISO week from Monday to following Monday
      - 'YYYY-MM' (e.g., '2026-09'): Calendar month from 1st of month to 1st of next month
    """
    period_clean = period_str.strip()
    match = PERIOD_REGEX.match(period_clean)
    if not match:
        raise ValueError(
            f"Invalid period: '{period_str}'. Expected 'last_7_days', 'last_30_days', "
            f"an ISO week ('YYYY-Www'), or a month ('YYYY-MM')."
        )
    
    if period_clean == "last_7_days":
        start_date = ref_date - timedelta(days=7)
        end_date = ref_date
    elif period_clean == "last_30_days":
        start_date = ref_date - timedelta(days=30)
        end_date = ref_date
    elif "-W" in period_clean:
        year_s, week_s = period_clean.split("-W")
        year = int(year_s)
        week = int(week_s)
        start_date = date.fromisocalendar(year, week, 1) # Monday
        end_date = start_date + timedelta(days=7)
    else: # YYYY-MM
        year_s, month_s = period_clean.split("-")
        year = int(year_s)
        month = int(month_s)
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

    return PeriodWindow(
        start=start_date.isoformat(),
        end_exclusive=end_date.isoformat()
    )
