def fmt_hhmm(minutes_in_day: int) -> str:
    h = minutes_in_day // 60
    m = minutes_in_day % 60
    return f"{h:02d}:{m:02d}"