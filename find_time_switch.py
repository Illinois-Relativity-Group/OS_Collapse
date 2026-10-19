#!/usr/bin/env python3
"""Find one change in monitor-row time spacing, allowing a mixed interval."""

import math
import re
from pathlib import Path
from statistics import median

MONITOR_FILE = (
    Path(__file__).resolve().parent
    / "data"
    / "Test_OS_collapse_magnetized_9000_16.mon"
)
REL_TOL = 1e-3
ABS_TOL = 1e-8


def close(a, b):
    return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def main():
    times = []
    file_lines = []
    steps_per_row = None

    with MONITOR_FILE.open() as stream:
        for line_number, line in enumerate(stream, start=1):
            match = re.search(r"Noting values every (\d+) time steps", line)
            if match:
                steps_per_row = int(match.group(1))

            text = line.split("#", 1)[0].strip()
            if not text:
                continue

            try:
                time = float(text.split()[0])
            except ValueError as exc:
                raise ValueError(
                    f"Invalid time on file line {line_number}"
                ) from exc
            if not math.isfinite(time):
                raise ValueError(f"Nonfinite time on file line {line_number}")
            times.append(time)
            file_lines.append(line_number)

    if len(times) < 3:
        raise ValueError("At least three data rows are required.")

    intervals = [b - a for a, b in zip(times, times[1:])]
    if any(dt <= 0 for dt in intervals):
        raise ValueError("Times must be strictly increasing.")

    before, after = intervals[0], intervals[-1]
    if close(before, after):
        raise ValueError(
            "No unique switch between two different constant intervals."
        )

    # Interval i connects zero-based data rows i and i + 1.
    start = next(
        i for i, dt in enumerate(intervals) if not close(dt, before)
    )
    end = start

    # A switch within a sampled interval can mix the old and new spacing.
    if not close(intervals[start], after):
        if not min(before, after) < intervals[start] < max(before, after):
            raise ValueError("Transition interval lies outside both spacings.")
        end += 1

    if end >= len(intervals) or any(
        not close(dt, after) for dt in intervals[end:]
    ):
        raise ValueError(
            "Expected one switch; found additional interval changes "
            "or more than one intermediate interval."
        )

    before_dt = median(intervals[:start])
    after_dt = median(intervals[end:])

    print(f"File: {MONITOR_FILE}")
    print(f"Data rows: {len(times)}")
    print(f"Before dt per recorded row: {before_dt:.12g}")
    print(f"After dt per recorded row:  {after_dt:.12g}")
    print(f"After / before ratio: {after_dt / before_dt:.12g}")

    if start == end:
        print(f"Switch at recorded time: {times[start]:.12g}")
    else:
        print(f"Mixed transition interval: {intervals[start]:.12g}")
        print(
            f"Switch time bracket: "
            f"[{times[start]:.12g}, {times[end]:.12g}]"
        )

    print(f"Boundary data rows (1-based): {start + 1} to {end + 1}")
    print(f"Boundary file lines: {file_lines[start]} to {file_lines[end]}")
    print(
        f"First full after interval: data rows {end + 1} to {end + 2}"
    )
    print(f"SWITCH_ROW_INDEX={end} (zero-based)")
    if steps_per_row:
        # First recorded index whose following interval uses the new dt.
        print(f"SWITCH_INDEX={end * steps_per_row}")
        print(f"Time steps per recorded row: {steps_per_row}")
        print(
            "Inferred switch step bracket (first data row = step 0): "
            f"[{start * steps_per_row}, {end * steps_per_row}]"
        )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Error: {exc}")
