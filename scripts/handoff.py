#!/usr/bin/env python3
"""Generate a standard handoff/completion report from a worktree."""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime
from pathlib import Path


def git(path: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=path, text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def now_display() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def read_validation(path: str | None) -> str:
    if not path:
        return "- Not provided"
    return Path(path).expanduser().read_text().strip() or "- Not provided"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--to", default="coordinator")
    parser.add_argument("--topic", default="Worktree handoff")
    parser.add_argument("--base", default=None)
    parser.add_argument("--validation-file")
    parser.add_argument("--output")
    args = parser.parse_args()

    path = Path(args.worktree).expanduser().resolve()
    base = args.base or git(path, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"]) or "HEAD~1"
    branch = git(path, ["branch", "--show-current"]) or "(detached)"
    head = git(path, ["rev-parse", "--short", "HEAD"]) or "unknown"
    status = git(path, ["status", "--short", "--untracked-files=all"]) or "clean"
    diff_stat = git(path, ["diff", "--stat", base]) or "- No diff stat"
    recent_commits = git(path, ["log", "--oneline", "--decorate", "-5"]) or "- No commits"
    changed_files = git(path, ["diff", "--name-only", base]) or "- No changed files"

    report = f"""# Completed: {args.topic}

From: {args.agent}
To: {args.to}
Date: {now_display()}
Status: unread

Summary:
- TBD

Worktree:
- Path: `{path}`
- Branch: `{branch}`
- HEAD: `{head}`
- Base: `{base}`

Changed files:
```text
{changed_files}
```

Git status:
```text
{status}
```

Diff stat:
```text
{diff_stat}
```

Recent commits:
```text
{recent_commits}
```

Validation:
```text
{read_validation(args.validation_file)}
```

Residual risk:
- TBD

Coordinator request:
- Review and decide merge/cherry-pick/manual follow-up.
"""

    if args.output:
        Path(args.output).expanduser().write_text(report)
        print(args.output)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
