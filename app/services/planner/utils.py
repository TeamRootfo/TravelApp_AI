import logging

logger = logging.getLogger(__name__)


def fmt_hhmm(minutes_in_day: int) -> str:
    logger.info(f"[fmt_hhmm] Formatting minutes: {minutes_in_day}")
    h = minutes_in_day // 60
    m = minutes_in_day % 60
    return f"{h:02d}:{m:02d}"
