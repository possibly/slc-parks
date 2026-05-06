#!/usr/bin/env python3
"""Generate history.json from git log of parks.csv.

For each commit that touched parks.csv, records the date, total park count,
and per-amenity Yes counts. The result is written to history.json so the
static site can render a chart without needing server-side git access.
"""

from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from pathlib import Path

OUTPUT_JSON = Path(__file__).with_name("history.json")

AMENITY_COLUMNS = [
    "Bathrooms", "Pool", "Pond", "Grills", "Pavillion", "Gardens",
    "Baseball Diamond", "Softball Diamond", "Toddler Friendly Play Area",
    "Kid Play Area", "Off Leash Dog Area", "Water Fountain", "Splash Pad",
    "Skate Park", "Basketball Court", "Disc Golf", "Beach Volleyball Court",
    "Volleyball Court", "Soccer Field", "River or Stream", "Tennis Courts",
    "Pickleball Courts", "Fitness Area", "Accessible Path", "Futsal Court",
    "Lighting After Dark", "Picnic Tables",
]


def git_log_commits() -> list[tuple[str, str]]:
    """Return list of (commit_hash, date) for all commits touching parks.csv."""
    result = subprocess.run(
        ["git", "log", "--follow", "--format=%H %as", "--", "parks.csv"],
        capture_output=True, text=True, check=True
    )
    commits = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            commits.append((parts[0], parts[1]))
    # Return in chronological order (oldest first)
    return list(reversed(commits))


def csv_at_commit(commit_hash: str) -> list[dict[str, str]]:
    """Return parsed parks.csv rows at the given git commit."""
    result = subprocess.run(
        ["git", "show", f"{commit_hash}:parks.csv"],
        capture_output=True, text=True, check=True
    )
    reader = csv.DictReader(io.StringIO(result.stdout))
    return list(reader)


def is_yes(value: str) -> bool:
    return str(value or "").strip().lower() == "yes"


def summarise(rows: list[dict[str, str]]) -> dict:
    amenities = {}
    for col in AMENITY_COLUMNS:
        count = sum(1 for row in rows if is_yes(row.get(col, "")))
        if count:
            amenities[col] = count
    return {
        "parks": len(rows),
        "amenities": amenities,
    }


def main() -> int:
    commits = git_log_commits()
    if not commits:
        print("No git commits found for parks.csv", file=sys.stderr)
        return 1

    entries = []
    seen_dates: dict[str, int] = {}  # date -> index in entries, for deduplication
    for commit_hash, date in commits:
        rows = csv_at_commit(commit_hash)
        summary = summarise(rows)
        entry = {"date": date, "commit": commit_hash[:8], **summary}
        if date in seen_dates:
            # Same day — overwrite with the latest commit for that day
            entries[seen_dates[date]] = entry
        else:
            seen_dates[date] = len(entries)
            entries.append(entry)

    OUTPUT_JSON.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_JSON} ({len(entries)} data points)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
