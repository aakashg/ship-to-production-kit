"""Read-only experiment: verify month-boundary reset math and model counter write load.
No network, no data access. Usage: python3 -I reset_time_check.py"""
from datetime import datetime, timezone


def next_reset(now):
    y, m = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
    return datetime(y, m, 1, tzinfo=timezone.utc)


cases = [
    datetime(2026, 11, 20, 13, 5, tzinfo=timezone.utc),
    datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
    datetime(2026, 2, 28, 23, 59, 59, tzinfo=timezone.utc),
    datetime(2028, 2, 29, 12, 0, tzinfo=timezone.utc),
    datetime(2026, 12, 1, 0, 0, 0, tzinfo=timezone.utc),
]
for c in cases:
    r = next_reset(c)
    print(f"now={c.isoformat()} reset={r.isoformat()} retry_after_s={int((r - c).total_seconds())}")

# Load model: ASSUMED inputs (no traffic data in this repo). M0 replaces them with real numbers.
peak_rps, hot_key_share = 2000, 0.2
print(f"assumed peak {peak_rps} req/s; hottest key {int(peak_rps * hot_key_share)} incr/s")
print("a per-request SQL row update on one hot key serializes on a row lock; use atomic INCR, flush in batches")
