#!/usr/bin/env python3
"""Small file-mailbox helper for multi-agent worktree coordination."""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path


SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def slug(value: str) -> str:
    cleaned = SAFE.sub("-", value.strip()).strip("-").lower()
    return cleaned or "message"


def signal_root(repo: str) -> Path:
    return Path(repo).expanduser().resolve() / ".mwa"


def ensure_boxes(root: Path, recipient: str) -> None:
    for box in ["inbox", "outbox", "done"]:
        (root / recipient / box).mkdir(parents=True, exist_ok=True)


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def now_display() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def read_body(args: argparse.Namespace) -> str:
    if args.body_file:
        return Path(args.body_file).read_text()
    if args.body:
        return args.body
    return ""


def cmd_send(args: argparse.Namespace) -> int:
    root = signal_root(args.root)
    ensure_boxes(root, args.to)
    ensure_boxes(root, args.sender)

    topic = args.topic.strip()
    filename = f"{now_stamp()}-{slug(args.sender)}-to-{slug(args.to)}-{slug(topic)}.md"
    body = read_body(args).strip()
    message = f"""# {topic}

From: {args.sender}
To: {args.to}
Date: {now_display()}
Status: unread

{body}
"""

    target = root / args.to / "inbox" / filename
    target.write_text(message)

    if args.outbox:
        outbox = root / args.sender / "outbox" / filename
        outbox.write_text(message.replace("Status: unread", "Status: sent", 1))

    print(target)
    return 0


def read_header(message: Path, key: str) -> str:
    prefix = f"{key}:"
    try:
        for line in message.read_text(errors="replace").splitlines()[:20]:
            if line.startswith(prefix):
                return line[len(prefix) :].strip()
    except OSError:
        return ""
    return ""


def list_messages(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(p for p in path.iterdir() if p.is_file())


def recipient_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    result = []
    for path in sorted(p for p in root.iterdir() if p.is_dir()):
        if all((path / box).is_dir() for box in ["inbox", "outbox", "done"]):
            result.append(path)
    return result


def cmd_inbox(args: argparse.Namespace) -> int:
    root = signal_root(args.root)
    inbox = root / args.recipient / "inbox"
    messages = list_messages(inbox)
    if not messages:
        print(f"No inbox messages for {args.recipient}")
        return 0
    for message in messages:
        print(message)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = signal_root(args.root)
    if not root.exists():
        print(f"No signal bus at {root}")
        return 0
    recipients = recipient_dirs(root)
    for recipient in recipients:
        inbox_count = len(list_messages(recipient / "inbox"))
        outbox_count = len(list_messages(recipient / "outbox"))
        done_count = len(list_messages(recipient / "done"))
        print(f"{recipient.name}: inbox={inbox_count} outbox={outbox_count} done={done_count}")
    return 0


def cmd_unread(args: argparse.Namespace) -> int:
    root = signal_root(args.root)
    recipients = [root / args.recipient] if args.recipient else recipient_dirs(root)
    found = False
    for recipient in recipients:
        messages = list_messages(recipient / "inbox")
        if not messages:
            continue
        found = True
        print(f"[{recipient.name}]")
        for message in messages:
            sender = read_header(message, "From") or "unknown"
            topic = message.stem
            print(f"- {message.name} from={sender} topic={topic}")
    if not found:
        print("No unread messages")
    return 0


def cmd_done(args: argparse.Namespace) -> int:
    root = signal_root(args.root)
    done_dir = root / args.recipient / "done"
    done_dir.mkdir(parents=True, exist_ok=True)

    source = Path(args.file)
    if not source.is_absolute():
        source = root / args.recipient / "inbox" / source
    if not source.exists():
        raise SystemExit(f"message not found: {source}")

    target = done_dir / source.name
    if target.exists() and not args.force:
        raise SystemExit(f"target exists, pass --force to replace: {target}")
    if target.exists():
        target.unlink()
    shutil.move(str(source), str(target))
    print(target)
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    root = signal_root(args.root)
    recipients = [root / args.recipient] if args.recipient else recipient_dirs(root)
    moved = 0
    for recipient in recipients:
        ensure_boxes(root, recipient.name)
        for message in list_messages(recipient / "inbox"):
            target = recipient / "done" / message.name
            if target.exists() and not args.force:
                print(f"Skipped existing {target}")
                continue
            if target.exists():
                target.unlink()
            shutil.move(str(message), str(target))
            moved += 1
            print(target)
    print(f"Archived {moved} message(s)")
    return 0


def cmd_reply(args: argparse.Namespace) -> int:
    root = signal_root(args.root)
    source = Path(args.file)
    if not source.is_absolute():
        source = root / args.sender / "inbox" / source
    if not source.exists():
        raise SystemExit(f"message not found: {source}")

    recipient = read_header(source, "From")
    if not recipient:
        raise SystemExit(f"cannot find From header in {source}")

    args.topic = args.topic or f"Re: {source.stem}"
    args.to = recipient
    args.outbox = True
    return cmd_send(args)


def cmd_nudge(args: argparse.Namespace) -> int:
    if not args.body:
        args.body = "Please send a brief status update, including current task, blockers, changed files, and next action."
    args.outbox = True
    return cmd_send(args)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    send = sub.add_parser("send", help="send a markdown message to a recipient inbox")
    send.add_argument("--root", required=True)
    send.add_argument("--from", dest="sender", required=True)
    send.add_argument("--to", required=True)
    send.add_argument("--topic", required=True)
    send.add_argument("--body", default="")
    send.add_argument("--body-file")
    send.add_argument("--outbox", action="store_true", help="also keep a sender outbox copy")
    send.set_defaults(func=cmd_send)

    inbox = sub.add_parser("inbox", help="list recipient inbox messages")
    inbox.add_argument("--root", required=True)
    inbox.add_argument("--recipient", required=True)
    inbox.set_defaults(func=cmd_inbox)

    status = sub.add_parser("status", help="summarize all signal bus inbox/outbox/done counts")
    status.add_argument("--root", required=True)
    status.set_defaults(func=cmd_status)

    unread = sub.add_parser("unread", help="list unread inbox messages for one recipient or all recipients")
    unread.add_argument("--root", required=True)
    unread.add_argument("--recipient")
    unread.set_defaults(func=cmd_unread)

    done = sub.add_parser("done", help="move an inbox message to done")
    done.add_argument("--root", required=True)
    done.add_argument("--recipient", required=True)
    done.add_argument("--file", required=True)
    done.add_argument("--force", action="store_true")
    done.set_defaults(func=cmd_done)

    archive = sub.add_parser("archive", help="move all inbox messages to done for one recipient or all recipients")
    archive.add_argument("--root", required=True)
    archive.add_argument("--recipient")
    archive.add_argument("--force", action="store_true")
    archive.set_defaults(func=cmd_archive)

    reply = sub.add_parser("reply", help="reply to a message sender")
    reply.add_argument("--root", required=True)
    reply.add_argument("--from", dest="sender", required=True)
    reply.add_argument("--file", required=True)
    reply.add_argument("--topic")
    reply.add_argument("--body", default="")
    reply.add_argument("--body-file")
    reply.set_defaults(func=cmd_reply)

    nudge = sub.add_parser("nudge", help="send a status-request nudge")
    nudge.add_argument("--root", required=True)
    nudge.add_argument("--from", dest="sender", required=True)
    nudge.add_argument("--to", required=True)
    nudge.add_argument("--topic", default="status nudge")
    nudge.add_argument("--body", default="")
    nudge.add_argument("--body-file")
    nudge.set_defaults(func=cmd_nudge)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
