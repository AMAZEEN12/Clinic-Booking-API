"""Prints a POST /reset body with weekday slots for the next N days (default 90).

Usage: python scripts/make_slots.py 90 > slots.json
Times are 09:00-16:00 Lagos time (UTC+1), every hour, two doctors alternating.
Times that have already passed today are left out.
"""

import json
import sys
from datetime import UTC, datetime, timedelta

days = int(sys.argv[1]) if len(sys.argv) > 1 else 90
providers = ["Dr. Bello", "Dr. Eze"]
now = datetime.now(UTC)
today = now.replace(hour=0, minute=0, second=0, microsecond=0)


def iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


slots = []
for offset in range(days):
    day = today + timedelta(days=offset)
    if day.weekday() >= 5:
        continue
    for i, hour in enumerate(range(8, 16)):
        start = day.replace(hour=hour)
        if start <= now:
            continue
        slots.append(
            {
                "id": f"slot-{start:%Y%m%d-%H%M}",
                "provider": providers[i % 2],
                "start": iso(start),
                "end": iso(start + timedelta(minutes=30)),
            }
        )

print(json.dumps({"slots": slots}, indent=2))
