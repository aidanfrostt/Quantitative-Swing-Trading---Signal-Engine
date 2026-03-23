"""
US equity (NYSE) session calendar via `exchange_calendars`.

Used by batch jobs to skip weekends/holidays (Kubernetes CronJob still fires; app exits 0).
"""

from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd

_ET = ZoneInfo("America/New_York")
_NYSE = xcals.get_calendar("XNYS")


def current_nyse_date() -> date:
    """Calendar date in America/New_York (for session checks)."""
    from datetime import datetime

    return datetime.now(_ET).date()


def is_nyse_trading_day(d: date) -> bool:
    """True if NYSE has a regular session on this calendar date."""
    ts = pd.Timestamp(d)
    return bool(_NYSE.is_session(ts))


