"""Create dated commits for each day in a configured date range."""

from __future__ import annotations

import os
import random
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path


# Configure these values before running the script.
START_DATE = "2025-03-03"
END_DATE = "2026-04-26"
SKIP_WEEKENDS = False
TIMEZONE_OFFSET = "+0000"
RANDOM_SEED = None

# Weighted commit counts. Most weekdays get 1 commit, some get none,
# and a few active days get 2-4 commits. Weekends are quiet by default.
WEEKDAY_COMMIT_WEIGHTS = {
    0: 18,
    1: 58,
    2: 17,
    3: 6,
    4: 1,
}
WEEKEND_COMMIT_WEIGHTS = {
    0: 82,
    1: 15,
    2: 3,
}


ROOT = Path(__file__).resolve().parent
LOG_FILE = ROOT / "activity_log.md"


def run_command(
    command: list[str], env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    return subprocess.run(
        command,
        cwd=ROOT,
        env=merged_env,
        text=True,
        capture_output=True,
        check=False,
    )


def parse_configured_date(value: str, name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must use YYYY-MM-DD format.") from exc


def date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def choose_commit_count(day: date) -> int:
    weights = WEEKEND_COMMIT_WEIGHTS if day.weekday() >= 5 else WEEKDAY_COMMIT_WEIGHTS
    counts = list(weights.keys())
    chances = list(weights.values())
    return random.choices(counts, weights=chances, k=1)[0]


def random_commit_datetimes(day: date, count: int) -> list[str]:
    start_seconds = 8 * 60 * 60
    end_seconds = 20 * 60 * 60
    selected_seconds = sorted(
        random.randint(start_seconds, end_seconds) for _ in range(count)
    )

    commit_dates = []
    for seconds in selected_seconds:
        commit_time = datetime.combine(day, datetime.min.time()) + timedelta(
            seconds=seconds
        )
        commit_dates.append(f"{commit_time:%Y-%m-%dT%H:%M:%S} {TIMEZONE_OFFSET}")

    return commit_dates


def ensure_git_repo() -> None:
    result = run_command(["git", "rev-parse", "--is-inside-work-tree"])
    if result.returncode != 0 or result.stdout.strip() != "true":
        raise RuntimeError("This script must be run from inside a Git repository.")


def append_activity_entry(day: date, commit_number: int, total_commits: int) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    note = "Backfilled GitHub contribution update"
    if total_commits > 1:
        note = f"{note} ({commit_number}/{total_commits})"

    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(f"- {day.isoformat()}: {note}.\n")


def create_commit(
    day: date, commit_date: str, commit_number: int, total_commits: int
) -> bool:
    append_activity_entry(day, commit_number, total_commits)

    add_result = run_command(["git", "add", "--", str(LOG_FILE.relative_to(ROOT))])
    if add_result.returncode != 0:
        print(f"Failed to stage {LOG_FILE.name} for {day}: {add_result.stderr.strip()}")
        return False

    commit_env = {
        "GIT_AUTHOR_DATE": commit_date,
        "GIT_COMMITTER_DATE": commit_date,
    }
    message = f"chore: daily update {day.isoformat()}"
    commit_result = run_command(["git", "commit", "-m", message], env=commit_env)
    if commit_result.returncode != 0:
        stderr = commit_result.stderr.strip()
        stdout = commit_result.stdout.strip()
        print(f"Failed to commit {day}: {stderr or stdout}")
        return False

    print(f"Created commit {commit_number}/{total_commits} for {day} at {commit_date}.")
    return True


def push_commits() -> bool:
    push_result = run_command(["git", "push", "origin", "main"])
    if push_result.returncode != 0:
        print(f"Failed to push commits: {push_result.stderr.strip()}")
        return False

    print("Pushed all backfilled commits to origin main.")
    return True


def main() -> int:
    try:
        start = parse_configured_date(START_DATE, "START_DATE")
        end = parse_configured_date(END_DATE, "END_DATE")
        if start > end:
            raise ValueError("START_DATE must be on or before END_DATE.")

        ensure_git_repo()
        if RANDOM_SEED is not None:
            random.seed(RANDOM_SEED)

        commits_created = 0
        for day in date_range(start, end):
            if SKIP_WEEKENDS and day.weekday() >= 5:
                print(f"Skipping weekend date {day}.")
                continue

            commit_dates = random_commit_datetimes(day, choose_commit_count(day))
            if not commit_dates:
                print(f"Skipping quiet date {day}.")
                continue

            total_commits = len(commit_dates)
            for index, commit_date in enumerate(commit_dates, start=1):
                if create_commit(day, commit_date, index, total_commits):
                    commits_created += 1

        if commits_created == 0:
            print("No commits were created; nothing to push.")
            return 0

        return 0 if push_commits() else 1
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"Backfill failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
