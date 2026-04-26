"""Append a daily activity entry, commit it, and push to GitHub."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOG_FILE = ROOT / "activity_log.md"


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command from the repository root and capture its output."""
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def append_activity_entry(today: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(f"- {today}: Daily GitHub contribution update.\n")


def has_changes_to_commit() -> bool:
    result = run_command(["git", "status", "--porcelain"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Unable to check git status.")
    return bool(result.stdout.strip())


def main() -> int:
    today = date.today().isoformat()
    append_activity_entry(today)

    try:
        add_result = run_command(["git", "add", "."])
        if add_result.returncode != 0:
            print(f"Failed to stage changes: {add_result.stderr.strip()}")
            return add_result.returncode

        if not has_changes_to_commit():
            print("No changes to commit.")
            return 0

        commit_message = f"chore: daily update {today}"
        commit_result = run_command(["git", "commit", "-m", commit_message])
        if commit_result.returncode != 0:
            stderr = commit_result.stderr.strip()
            stdout = commit_result.stdout.strip()
            print(f"Failed to commit changes: {stderr or stdout}")
            return commit_result.returncode

        push_result = run_command(["git", "push", "origin", "main"])
        if push_result.returncode != 0:
            print(f"Failed to push changes: {push_result.stderr.strip()}")
            return push_result.returncode

        print(f"Committed and pushed daily update for {today}.")
        return 0
    except FileNotFoundError as exc:
        print(f"Required command not found: {exc.filename}")
        return 1
    except RuntimeError as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
