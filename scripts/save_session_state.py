#!/usr/bin/env python3
"""Auto-save session state to project memory on exit (Stop hook)."""

import os
import subprocess
from datetime import datetime

PROJECT_DIR = "/Volumes/Frank1T/VibeCoding/Rotation_Strategy_v3.2"
MEMORY_DIR = os.path.expanduser(
    "~/.claude/projects/-Volumes-Frank1T-VibeCoding-Rotation-Strategy-v3-2/memory/"
)
DEBOUNCE_MINUTES = 30


def run(cmd: str) -> str:
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=PROJECT_DIR
    )
    return result.stdout.strip()


def save_state() -> None:
    # Dedup: skip if recently saved (avoids noise on /clear, compact, etc.)
    state_file = os.path.join(MEMORY_DIR, "session_state.md")
    if os.path.exists(state_file):
        age_seconds = datetime.now().timestamp() - os.path.getmtime(state_file)
        if age_seconds < DEBOUNCE_MINUTES * 60:
            return

    branch = run("git branch --show-current")
    status = run("git status --short")
    diff = run("git diff --stat")
    log = run("git log --oneline -6")

    os.makedirs(MEMORY_DIR, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    body = f"""---
name: session-state
description: Auto-saved v3.2 session state — branch, uncommitted work, recent commits
metadata:
  type: project
---

## Session State (auto-saved {now})

**Branch:** `{branch}`

**Recent commits:**
{chr(10).join(f'- {l}' for l in log.split(chr(10))) if log else '- (none)'}

**Uncommitted changes:**
{status if status else '- clean working tree'}

**Diff summary:**
{diff if diff else '- (none)'}
"""
    with open(state_file, "w") as f:
        f.write(body)

    # Update MEMORY.md index
    index_file = os.path.join(MEMORY_DIR, "MEMORY.md")
    entry = "- [Session State](session_state.md) — Auto-saved project state from last session"

    if os.path.exists(index_file):
        with open(index_file) as f:
            lines = f.read().strip().split("\n")
        # Remove old entry for this file, then append
        lines = [l for l in lines if "session_state.md" not in l]
        lines.append(entry)
        with open(index_file, "w") as f:
            f.write("\n".join(lines) + "\n")
    else:
        with open(index_file, "w") as f:
            f.write(entry + "\n")


if __name__ == "__main__":
    save_state()
