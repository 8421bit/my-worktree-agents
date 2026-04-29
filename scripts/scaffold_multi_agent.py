#!/usr/bin/env python3
"""Create confirmed multi-agent Git worktrees and local coordination files."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT_BLOCK_BEGIN = "<!-- MWA:BEGIN -->"
ROOT_BLOCK_END = "<!-- MWA:END -->"


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def git_ok(cmd: list[str], cwd: Path) -> bool:
    return subprocess.run(cmd, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def mkdirs(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def render_list(items: list[str]) -> str:
    if not items:
        return "- TBD"
    return "\n".join(f"- {item}" for item in items)


def render_code_lines(items: list[str]) -> str:
    if not items:
        return "TBD\n"
    return "\n".join(items) + "\n"


def write_text(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        print(f"Preserved existing {path}")
        return
    path.write_text(content)


def replace_marked_block(existing: str, block: str) -> str:
    start = existing.find(ROOT_BLOCK_BEGIN)
    end = existing.find(ROOT_BLOCK_END)
    if start != -1 and end != -1 and end > start:
        end += len(ROOT_BLOCK_END)
        prefix = existing[:start].rstrip()
        suffix = existing[end:].lstrip()
        parts = [part for part in [prefix, block.strip(), suffix] if part]
        return "\n\n".join(parts) + "\n"
    if existing.strip():
        return existing.rstrip() + "\n\n" + block.strip() + "\n"
    return block.strip() + "\n"


def root_doc(repo: Path, agents: list[dict]) -> str:
    agent_lines = []
    for agent in agents:
        name = agent["name"]
        worktree = agent.get("worktree", f".worktrees/{name}")
        role = agent.get("role", name)
        allowed = ", ".join(agent.get("allowed_paths", [])) or "TBD"
        forbidden = ", ".join(agent.get("forbidden_paths", [])) or "TBD"
        agent_lines.append(
            f"- `{name}` ({role}): `{worktree}`; allowed: {allowed}; forbidden: {forbidden}"
        )
    rendered_agents = "\n".join(agent_lines) if agent_lines else "- TBD"
    return f"""{ROOT_BLOCK_BEGIN}
## My Worktree Agents

This repository uses `my-worktree-agents` for local multi-agent coordination.

Coordinator workspace:

```text
{repo}
```

Local coordination state:

```text
{repo}/.mwa/
```

Rules:

- Check `.mwa/coordinator/inbox/` before starting, resuming, and final reporting.
- Branch agents work in their assigned Git worktrees and must stay inside their allowed write scopes.
- Cross-scope changes require a message to `.mwa/coordinator/inbox/`.
- Shared memory lives in `.mwa/memory/`; branch agents propose updates, coordinator accepts them.
- Local task files and reports are coordination state, not source deliverables unless explicitly promoted.
- Use `worktree_status.py` for read-only integration audits before merge/cherry-pick.

Agents:

{rendered_agents}
{ROOT_BLOCK_END}"""


def write_root_docs(repo: Path, agents: list[dict], force: bool) -> None:
    block = root_doc(repo, agents)
    for filename in ["AGENTS.md", "CLAUDE.md"]:
        path = repo / filename
        existing = path.read_text() if path.exists() else ""
        if path.exists() and not force and ROOT_BLOCK_BEGIN not in existing and existing.strip():
            print(f"Appended MWA block to existing {path}")
        path.write_text(replace_marked_block(existing, block))


def agent_doc(repo: Path, agent: dict) -> str:
    name = agent["name"]
    role = agent.get("role", name)
    worktree = agent.get("worktree", f".worktrees/{name}")
    return f"""# Agent: {role}

## Workspace

You are in:

```text
{repo}/{worktree}
```

This is a branch-agent worktree. The coordinator works in:

```text
{repo}
```

## Responsibilities

{render_list(agent.get("responsibilities", []))}

## Allowed Writes

```text
{render_code_lines(agent.get("allowed_paths", []))}```

## Forbidden Writes

```text
{render_code_lines(agent.get("forbidden_paths", []))}```

## Signal Bus

All agents use:

```text
{repo}/.mwa/
```

Your inbox:

```text
{repo}/.mwa/{name}/inbox/
```

Rules:

- Check your inbox before starting work, resuming work, and handing off.
- Read shared memory at `{repo}/.mwa/memory/shared.md` before major planning.
- Send coordinator messages to `{repo}/.mwa/coordinator/inbox/`.
- Send other agent messages to that agent's `inbox/`.
- Move handled messages to your own `done/`.
- Keep a copy in your own `outbox/` when useful.
- Use `agent_signal.py inbox/send/done/status` when available.
- Use `agent_memory.py propose` to request shared-memory updates; do not edit shared memory directly unless coordinator authorizes it.
- Use `worktree_status.py` for read-only closeout checks when requested by coordinator.

## Cross-Scope Work

Do not edit outside your allowed write scope.

When blocked:

```text
[BLOCKED -> coordinator]
Summary:
Needs:
Files affected:
Decision required:
```

## Local Task Files

- Keep local `TASKS_{name.upper().replace('-', '_')}.md` and `*-REPORT.md` only in this worktree.
- Do not merge local task/report files to main.
- Long-lived backlog items go through coordinator.
- Keep your task file updated by stage: Discover, Plan, Implement, Verify, Handoff.

## Verification

```bash
{render_code_lines(agent.get("verification", []))}```
"""


def task_doc(agent: dict) -> str:
    name = agent["name"]
    title = f"TASKS_{name.upper().replace('AGENT-', '').replace('-', '_')}"
    return f"""# {title}

Local tasks for `{name}`. Do not merge this file to the coordinator branch.

## Inbox

- Check `.mwa/{name}/inbox/` before starting or resuming.

## Active Task

- TBD

## Discover

- Context read:
- Key findings:
- Open questions:

## Plan

- Scope:
- Files expected:
- Verification:

## Implement

- Changed files:
- Notes:

## Verify

- Commands run:
- Results:
- Remaining risk:

## Blockers

```text
[BLOCKED -> coordinator]
Summary:
Needs:
Files affected:
Decision required:
```

## Handoff

- Summary:
- Changed files:
- Validation:
- Coordinator request:
"""


def ensure_gitignore(repo: Path) -> None:
    ignore = repo / ".gitignore"
    existing = ignore.read_text() if ignore.exists() else ""
    additions = [
        ".worktrees/",
        ".mwa/",
        "TASKS_*.md",
        "*-REPORT.md",
        "REPORT*.md",
    ]
    missing = [item for item in additions if item not in existing.splitlines()]
    if missing:
        with ignore.open("a") as fh:
            if existing and not existing.endswith("\n"):
                fh.write("\n")
            fh.write("\n# Multi-agent local coordination\n")
            for item in missing:
                fh.write(f"{item}\n")


def ensure_memory(signal_root: Path) -> None:
    memory_root = signal_root / "memory"
    mkdirs(memory_root / "proposals")
    defaults = {
        "shared.md": "# Shared Memory\n\nCoordinator-approved long-lived project facts.\n",
        "decisions.md": "# Decisions\n\nCoordinator-approved decisions that affect multiple agents.\n",
        "glossary.md": "# Glossary\n\nShared project terms.\n",
    }
    for name, content in defaults.items():
        path = memory_root / name
        if not path.exists():
            path.write_text(content)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--topology", required=True)
    parser.add_argument("--no-worktrees", action="store_true")
    parser.add_argument("--force", action="store_true", help="overwrite existing AGENTS/CLAUDE/task files")
    parser.add_argument(
        "--write-root-docs",
        action="store_true",
        help="create or update root AGENTS.md and CLAUDE.md with a marked MWA coordinator block",
    )
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    topology = json.loads(Path(args.topology).read_text())
    base_branch = topology.get("base_branch", "main")
    worktree_root = repo / topology.get("worktree_root", ".worktrees")
    signal_root = repo / topology.get("signal_root", ".mwa")
    agents = topology.get("agents", [])

    for recipient in ["coordinator", *[a["name"] for a in agents]]:
        for box in ["inbox", "outbox", "done"]:
            mkdirs(signal_root / recipient / box)
    ensure_memory(signal_root)

    mkdirs(worktree_root)
    ensure_gitignore(repo)

    root_tasks = repo / "TASKS.md"
    if not root_tasks.exists():
        root_tasks.write_text("# TASKS\n\nCoordinator-owned backlog.\n")
    if args.write_root_docs:
        write_root_docs(repo, agents, args.force)

    for agent in agents:
        name = agent["name"]
        branch = agent.get("branch", f"feat/{name}")
        rel_worktree = Path(agent.get("worktree", f".worktrees/{name}"))
        worktree_path = repo / rel_worktree

        if not args.no_worktrees and not worktree_path.exists():
            run(["git", "worktree", "add", str(worktree_path), "-b", branch, base_branch], repo)

        mkdirs(worktree_path)
        doc = agent_doc(repo, {**agent, "worktree": str(rel_worktree)})
        write_text(worktree_path / "AGENTS.md", doc, args.force)
        write_text(worktree_path / "CLAUDE.md", doc, args.force)
        task_name = f"TASKS_{name.upper().replace('AGENT-', '').replace('-', '_')}.md"
        task_file = worktree_path / task_name
        write_text(task_file, task_doc(agent), args.force)
        if not args.no_worktrees:
            if git_ok(["git", "ls-files", "--error-unmatch", "CLAUDE.md"], worktree_path):
                run(["git", "update-index", "--skip-worktree", "CLAUDE.md"], worktree_path)

    print(f"Created signal bus at {signal_root}")
    print(f"Configured {len(agents)} agent worktree(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
