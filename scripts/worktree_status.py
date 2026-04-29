#!/usr/bin/env python3
"""Read-only Git worktree status report for multi-agent coordination."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


LOCAL_ONLY_NAMES = {
    "AGENTS.md",
    "CLAUDE.md",
    "TASK.md",
    "TASK2.md",
}


def run_git(repo: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def try_git(repo: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def parse_worktrees(repo: Path) -> list[dict[str, str]]:
    output = run_git(repo, ["worktree", "list", "--porcelain"])
    items: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in output.splitlines():
        if not line:
            if current:
                items.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current["path"] = value
        elif key in {"HEAD", "branch", "detached"}:
            current[key.lower()] = value or "true"
    if current:
        items.append(current)
    return items


def local_only(path: str) -> bool:
    name = Path(path).name
    return name in LOCAL_ONLY_NAMES or name.startswith("TASKS_") or name.endswith("-REPORT.md") or name.startswith("REPORT")


def load_topology(path: str | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).expanduser().read_text())


def agent_by_path(topology: dict, root: Path, path: Path) -> dict:
    for agent in topology.get("agents", []):
        worktree = root / agent.get("worktree", f".worktrees/{agent['name']}")
        if worktree.resolve() == path.resolve():
            return agent
    return {}


def changed_files(path: Path, base: str) -> list[str]:
    files = set()
    for args in [
        ["diff", "--name-only", base],
        ["diff", "--cached", "--name-only", base],
        ["ls-files", "--others", "--exclude-standard"],
    ]:
        for line in try_git(path, args).splitlines():
            if line:
                files.add(line.strip())
    return sorted(files)


def path_matches(file: str, patterns: list[str]) -> bool:
    return any(file == pattern.rstrip("/") or file.startswith(pattern.rstrip("/") + "/") for pattern in patterns)


def scope_violations(files: list[str], agent: dict) -> list[str]:
    if not agent:
        return []
    allowed = agent.get("allowed_paths", [])
    forbidden = agent.get("forbidden_paths", [])
    violations = []
    for file in files:
        if local_only(file):
            continue
        if forbidden and path_matches(file, forbidden):
            violations.append(f"{file} violates forbidden_paths")
            continue
        if allowed and not path_matches(file, allowed):
            violations.append(f"{file} is outside allowed_paths")
    return violations


def merge_recommendation(item: dict) -> str:
    if item["scope_violations"]:
        return "manual review: scope violations"
    if item["source_dirty_files"]:
        return "wait: source dirty files"
    if item["ahead"] not in {"0", "?", ""}:
        return "review commits: merge or cherry-pick"
    if item["local_only_dirty_files"]:
        return "local-only changes: preserve or ignore"
    return "no action"


def status_for_worktree(root: Path, path: Path, base: str, topology: dict) -> dict:
    branch = try_git(path, ["branch", "--show-current"]) or "(detached)"
    status_lines = try_git(path, ["status", "--short", "--untracked-files=all"]).splitlines()
    files = [line[3:] if len(line) > 3 else line for line in status_lines]
    source_files = [f for f in files if not local_only(f)]
    local_files = [f for f in files if local_only(f)]
    all_changed_files = changed_files(path, base)
    agent = agent_by_path(topology, root, path)

    ahead_behind = try_git(path, ["rev-list", "--left-right", "--count", f"{base}...HEAD"])
    ahead = behind = "?"
    if ahead_behind:
        left, _, right = ahead_behind.partition("\t")
        behind = left.strip()
        ahead = right.strip()

    diff_stat = try_git(path, ["diff", "--stat", base])
    item = {
        "path": str(path),
        "branch": branch,
        "agent": agent.get("name", ""),
        "dirty": bool(status_lines),
        "ahead": ahead,
        "behind": behind,
        "source_dirty_files": source_files,
        "local_only_dirty_files": local_files,
        "changed_files": all_changed_files,
        "scope_violations": scope_violations(all_changed_files, agent),
        "diff_stat": diff_stat,
    }
    item["merge_recommendation"] = merge_recommendation(item)
    return item


def print_text(report: list[dict]) -> None:
    for item in report:
        print(f"## {item['branch']} :: {item['path']}")
        if item["agent"]:
            print(f"agent={item['agent']}")
        print(f"dirty={item['dirty']} ahead={item['ahead']} behind={item['behind']}")
        print(f"merge_recommendation={item['merge_recommendation']}")
        if item["source_dirty_files"]:
            print("source dirty files:")
            for file in item["source_dirty_files"]:
                print(f"- {file}")
        if item["local_only_dirty_files"]:
            print("local-only dirty files:")
            for file in item["local_only_dirty_files"]:
                print(f"- {file}")
        if item["scope_violations"]:
            print("scope violations:")
            for violation in item["scope_violations"]:
                print(f"- {violation}")
        if item["diff_stat"]:
            print("diff stat:")
            print(item["diff_stat"])
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--base", default=None, help="base branch/ref for ahead/behind and diff; default current root branch")
    parser.add_argument("--topology", help="confirmed topology JSON for write-scope validation")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    base = args.base or try_git(root, ["branch", "--show-current"]) or "HEAD"
    topology = load_topology(args.topology)
    worktrees = parse_worktrees(root)
    report = [status_for_worktree(root, Path(item["path"]), base, topology) for item in worktrees]

    if args.json:
        print(json.dumps({"base": base, "worktrees": report}, indent=2))
    else:
        print(f"Base: {base}")
        print()
        print_text(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
