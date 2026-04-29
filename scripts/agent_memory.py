#!/usr/bin/env python3
"""Shared memory helper stored under .mwa/memory."""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path


SAFE = re.compile(r"[^A-Za-z0-9._-]+")
MEMORY_FILES = {"shared", "decisions", "glossary"}


def slug(value: str) -> str:
    cleaned = SAFE.sub("-", value.strip()).strip("-").lower()
    return cleaned or "memory"


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def now_display() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def memory_root(repo: str) -> Path:
    return Path(repo).expanduser().resolve() / ".mwa" / "memory"


def ensure_memory(root: Path) -> None:
    (root / "proposals").mkdir(parents=True, exist_ok=True)
    defaults = {
        "shared.md": "# Shared Memory\n\nCoordinator-approved long-lived project facts.\n",
        "decisions.md": "# Decisions\n\nCoordinator-approved decisions that affect multiple agents.\n",
        "glossary.md": "# Glossary\n\nShared project terms.\n",
    }
    for name, content in defaults.items():
        path = root / name
        if not path.exists():
            path.write_text(content)


def target_file(root: Path, target: str) -> Path:
    if target not in MEMORY_FILES:
        raise SystemExit(f"target must be one of: {', '.join(sorted(MEMORY_FILES))}")
    return root / f"{target}.md"


def read_text_arg(args: argparse.Namespace) -> str:
    if args.body_file:
        return Path(args.body_file).expanduser().read_text().strip()
    if args.body:
        return args.body.strip()
    return ""


def cmd_init(args: argparse.Namespace) -> int:
    root = memory_root(args.root)
    ensure_memory(root)
    print(root)
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    root = memory_root(args.root)
    ensure_memory(root)
    if args.target == "all":
        for target in ["shared", "decisions", "glossary"]:
            path = target_file(root, target)
            print(f"===== {path.name} =====")
            print(path.read_text())
        return 0
    print(target_file(root, args.target).read_text())
    return 0


def cmd_propose(args: argparse.Namespace) -> int:
    root = memory_root(args.root)
    ensure_memory(root)
    body = read_text_arg(args)
    if not body:
        raise SystemExit("proposal body is required")
    filename = f"{now_stamp()}-{slug(args.sender)}-{slug(args.target)}-{slug(args.topic)}.md"
    proposal = root / "proposals" / filename
    proposal.write_text(
        f"""# Memory Proposal: {args.topic}

From: {args.sender}
Target: {args.target}
Date: {now_display()}
Status: proposed

{body}
"""
    )
    print(proposal)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    root = memory_root(args.root)
    ensure_memory(root)
    proposals = sorted((root / "proposals").glob("*.md"))
    if not proposals:
        print("No memory proposals")
        return 0
    for proposal in proposals:
        print(proposal)
    return 0


def extract_target(proposal: Path) -> str:
    for line in proposal.read_text(errors="replace").splitlines()[:20]:
        if line.startswith("Target:"):
            return line.partition(":")[2].strip()
    raise SystemExit(f"proposal missing Target header: {proposal}")


def cmd_accept(args: argparse.Namespace) -> int:
    root = memory_root(args.root)
    ensure_memory(root)
    proposal = Path(args.file)
    if not proposal.is_absolute():
        proposal = root / "proposals" / proposal
    if not proposal.exists():
        raise SystemExit(f"proposal not found: {proposal}")
    target = target_file(root, args.target or extract_target(proposal))
    content = proposal.read_text().strip()
    with target.open("a") as fh:
        fh.write("\n\n---\n\n")
        fh.write(content.replace("Status: proposed", "Status: accepted", 1))
        fh.write("\n")
    accepted_dir = root / "proposals" / "accepted"
    accepted_dir.mkdir(parents=True, exist_ok=True)
    destination = accepted_dir / proposal.name
    if destination.exists():
        destination.unlink()
    shutil.move(str(proposal), str(destination))
    print(target)
    return 0


def cmd_append(args: argparse.Namespace) -> int:
    root = memory_root(args.root)
    ensure_memory(root)
    body = read_text_arg(args)
    if not body:
        raise SystemExit("body is required")
    path = target_file(root, args.target)
    with path.open("a") as fh:
        fh.write("\n\n---\n\n")
        fh.write(f"Date: {now_display()}\n")
        fh.write(f"By: {args.sender}\n\n")
        fh.write(body)
        fh.write("\n")
    print(path)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="initialize .mwa/memory")
    init.add_argument("--root", required=True)
    init.set_defaults(func=cmd_init)

    read = sub.add_parser("read", help="read shared memory")
    read.add_argument("--root", required=True)
    read.add_argument("--target", choices=["all", *sorted(MEMORY_FILES)], default="all")
    read.set_defaults(func=cmd_read)

    propose = sub.add_parser("propose", help="write a memory proposal for coordinator review")
    propose.add_argument("--root", required=True)
    propose.add_argument("--from", dest="sender", required=True)
    propose.add_argument("--target", choices=sorted(MEMORY_FILES), default="shared")
    propose.add_argument("--topic", required=True)
    propose.add_argument("--body", default="")
    propose.add_argument("--body-file")
    propose.set_defaults(func=cmd_propose)

    list_cmd = sub.add_parser("list", help="list pending memory proposals")
    list_cmd.add_argument("--root", required=True)
    list_cmd.set_defaults(func=cmd_list)

    accept = sub.add_parser("accept", help="coordinator accepts a proposal into shared memory")
    accept.add_argument("--root", required=True)
    accept.add_argument("--file", required=True)
    accept.add_argument("--target", choices=sorted(MEMORY_FILES))
    accept.set_defaults(func=cmd_accept)

    append = sub.add_parser("append", help="coordinator appends directly to memory")
    append.add_argument("--root", required=True)
    append.add_argument("--from", dest="sender", default="coordinator")
    append.add_argument("--target", choices=sorted(MEMORY_FILES), default="shared")
    append.add_argument("--body", default="")
    append.add_argument("--body-file")
    append.set_defaults(func=cmd_append)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
