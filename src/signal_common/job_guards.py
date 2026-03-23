"""
Early exits for market-dependent batch jobs.

Call at the start of `run()` so CronJobs on holidays are no-ops (exit code 0).
"""

from __future__ import annotations

import logging
import sys

from signal_common.market_calendar import current_nyse_date, is_nyse_trading_day

logger = logging.getLogger(__name__)


def exit_if_not_nyse_trading_day() -> None:
    """Call at start of market-dependent cron jobs; exits 0 if today is not an NYSE session."""
    d = current_nyse_date()
    if not is_nyse_trading_day(d):
        logger.info("Skipping job: %s is not an NYSE trading day", d)
        sys.exit(0)
