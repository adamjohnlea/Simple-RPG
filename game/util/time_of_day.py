from __future__ import annotations
from dataclasses import dataclass


@dataclass
class _TimeOfDay:
    # minutes from 0..1439 (00:00..23:59). Keep as float to accumulate fractions smoothly.
    minutes: float = 8 * 60.0  # start morning 08:00 by default
    # scale: how many in-game minutes per real second
    minutes_per_second: float = 5.0  # fast for demo

    def advance_ms(self, dt_ms: float):
        inc_min = self.minutes_per_second * (dt_ms / 1000.0)
        # accumulate without truncation; wrap around 24h
        self.minutes = (self.minutes + inc_min) % (24 * 60)

    def add_minutes(self, mins: int):
        # Convenience for debug time skipping
        self.minutes = (self.minutes + float(mins)) % (24 * 60)

    def set_morning(self):
        # Morning at 08:00
        self.minutes = 8 * 60.0

    def is_evening(self) -> bool:
        # 18:00-20:00
        return 18 * 60 <= self.minutes < 20 * 60

    def is_night(self) -> bool:
        # 20:00-06:00
        m = self.minutes
        return m >= 20 * 60 or m < 6 * 60

    def is_shop_open(self) -> bool:
        # shop open 08:00–20:00
        return 8 * 60 <= self.minutes < 20 * 60

    def clock_text(self) -> str:
        total = int(self.minutes)  # convert to whole minutes for display
        h24 = (total // 60) % 24
        m = total % 60
        am = h24 < 12
        h12 = h24 % 12
        if h12 == 0:
            h12 = 12
        suffix = "AM" if am else "PM"
        return f"{h12}:{m:02d} {suffix}"


# Singleton-like instance
TimeOfDay = _TimeOfDay()