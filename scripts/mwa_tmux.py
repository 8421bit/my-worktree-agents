#!/usr/bin/env python3
"""Auto-detected tmux runner and notifier for My Worktree Agents.

The file mailbox under .mwa/ remains the source of truth. This helper only
adds live tmux sessions and inbox notifications when tmux is available. If
tmux is not installed, the normal file-mailbox workflow remains unchanged.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path


DEFAULT_SESSION = "mwa"
DEFAULT_NOTIFY_MODE = "display"
VALID_NOTIFY_MODES = {"codex-prompt", "display", "send-keys"}


def tmux_bin() -> str | None:
    return shutil.which("tmux")


def require_tmux() -> str:
    binary = tmux_bin()
    if not binary:
        raise SystemExit("tmux is not installed. Continue with the normal .mwa file-mailbox workflow.")
    return binary


def run_tmux(args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    binary = require_tmux()
    return subprocess.run([binary, *args], text=True, capture_output=True, check=check)


def repo_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def signal_root(repo: Path) -> Path:
    return repo / ".mwa"


def runtime_root(repo: Path) -> Path:
    path = signal_root(repo) / "runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_topology(path: str | None) -> dict:
    if not path:
        return {"agents": []}
    topology_path = Path(path).expanduser()
    if not topology_path.exists():
        raise SystemExit(f"topology file not found: {topology_path}")
    return json.loads(topology_path.read_text())


def agent_worktree(repo: Path, topology: dict, agent: dict) -> Path:
    rel = agent.get("worktree") or f"{topology.get('worktree_root', '.worktrees')}/{agent['name']}"
    return (repo / rel).resolve()


def tmux_config_path(repo: Path) -> Path:
    return signal_root(repo) / "tmux.json"


def seen_path(repo: Path, session: str) -> Path:
    return runtime_root(repo) / f"tmux-seen-{session}.json"


def session_exists(session: str) -> bool:
    return run_tmux(["has-session", "-t", session], check=False).returncode == 0


def window_exists(session: str, window: str) -> bool:
    result = run_tmux(["list-windows", "-t", session, "-F", "#{window_name}"], check=False)
    return result.returncode == 0 and window in result.stdout.splitlines()


def target_exists(target: str) -> bool:
    result = run_tmux(["display-message", "-p", "-t", target, "#{session_name}:#{window_name}"], check=False)
    return result.returncode == 0


def shell_command() -> str:
    return "${SHELL:-/bin/sh}"


def format_command(template: str, repo: Path, recipient: str, worktree: Path) -> str:
    return template.format(
        repo=str(repo),
        recipient=recipient,
        agent=recipient,
        worktree=str(worktree),
    )


def configured_window(config: dict, recipient: str) -> dict[str, str] | None:
    raw = config.get("targets", {}).get(recipient)
    if isinstance(raw, str):
        return {"target": raw}
    if isinstance(raw, dict) and raw.get("target"):
        return {str(key): str(value) for key, value in raw.items()}
    return None


def write_config(repo: Path, session: str, windows: dict[str, dict[str, str]]) -> None:
    root = signal_root(repo)
    root.mkdir(parents=True, exist_ok=True)
    tmux_config_path(repo).write_text(
        json.dumps(
            {
                "session": session,
                "updated_at": datetime.now().astimezone().isoformat(),
                "windows": windows,
            },
            indent=2,
        )
        + "\n"
    )


def cmd_check(args: argparse.Namespace) -> int:
    binary = tmux_bin()
    if binary:
        version = subprocess.run([binary, "-V"], text=True, capture_output=True, check=False).stdout.strip()
        print(f"tmux available: {binary} ({version})")
    else:
        print("tmux not installed; use the normal .mwa file-mailbox workflow")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    require_tmux()
    return start_tmux(args)


def cmd_auto(args: argparse.Namespace) -> int:
    if not tmux_bin():
        print("tmux not installed; using the normal .mwa file-mailbox workflow")
        return 0
    return start_tmux(args)


def start_tmux(args: argparse.Namespace) -> int:
    repo = repo_path(args.root)
    topology = load_topology(args.topology)
    tmux_config = topology.get("tmux", {})
    session = args.session or tmux_config.get("session") or DEFAULT_SESSION
    coordinator_command = args.coordinator_command or tmux_config.get("coordinator_command") or shell_command()
    agent_command = args.agent_command or tmux_config.get("agent_command") or shell_command()

    windows: dict[str, dict[str, str]] = {}
    coordinator_window = configured_window(tmux_config, "coordinator")
    if coordinator_window:
        windows["coordinator"] = {"cwd": str(repo), **coordinator_window}
    else:
        if not session_exists(session):
            run_tmux(["new-session", "-d", "-s", session, "-n", "coordinator", "-c", str(repo), coordinator_command])
        elif not window_exists(session, "coordinator"):
            run_tmux(["new-window", "-d", "-t", session, "-n", "coordinator", "-c", str(repo), coordinator_command])
        windows["coordinator"] = {"target": f"{session}:coordinator", "cwd": str(repo)}

    for agent in topology.get("agents", []):
        name = agent["name"]
        worktree = agent_worktree(repo, topology, agent)
        agent_window = agent.get("tmux_target")
        if isinstance(agent_window, str):
            agent_window = {"target": agent_window}
        agent_window = agent_window or configured_window(tmux_config, name)
        if agent_window:
            windows[name] = {"cwd": str(worktree), **{str(key): str(value) for key, value in agent_window.items()}}
        else:
            command = format_command(agent.get("tmux_command") or agent_command, repo, name, worktree)
            if not window_exists(session, name):
                run_tmux(["new-window", "-d", "-t", session, "-n", name, "-c", str(worktree), command])
            windows[name] = {"target": f"{session}:{name}", "cwd": str(worktree)}

    write_config(repo, session, windows)
    print(f"tmux session ready: {session}")
    print(f"config: {tmux_config_path(repo)}")
    print(f"attach: tmux attach -t {session}")
    return 0


def load_config(repo: Path, session: str | None) -> dict:
    path = tmux_config_path(repo)
    if path.exists():
        config = json.loads(path.read_text())
        if session:
            config["session"] = session
        return config
    return {"session": session or DEFAULT_SESSION, "windows": {}}


def cmd_attach(args: argparse.Namespace) -> int:
    repo = repo_path(args.root)
    config = load_config(repo, args.session)
    run_tmux(["attach", "-t", config["session"]], check=True)
    return 0


def list_inbox_messages(repo: Path) -> dict[str, list[Path]]:
    root = signal_root(repo)
    result: dict[str, list[Path]] = {}
    if not root.exists():
        return result
    for recipient in sorted(path for path in root.iterdir() if path.is_dir()):
        inbox = recipient / "inbox"
        if not inbox.is_dir():
            continue
        messages = sorted(path for path in inbox.iterdir() if path.is_file())
        if messages:
            result[recipient.name] = messages
    return result


def load_seen(repo: Path, session: str) -> set[str]:
    path = seen_path(repo, session)
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text()).get("seen", []))
    except json.JSONDecodeError:
        return set()


def save_seen(repo: Path, session: str, seen: set[str]) -> None:
    seen_path(repo, session).write_text(json.dumps({"seen": sorted(seen)}, indent=2) + "\n")


def notify_mode(config: dict, args_mode: str | None = None) -> str:
    mode = args_mode or config.get("notify_mode") or DEFAULT_NOTIFY_MODE
    if mode not in VALID_NOTIFY_MODES:
        raise SystemExit(f"notify mode must be one of: {', '.join(sorted(VALID_NOTIFY_MODES))}")
    return mode


def notify_text(recipient: str, message: Path) -> str:
    return (
        f"MWA inbox: {message.name}. "
        f"Please read .mwa/{recipient}/inbox, handle the message, and move it to done."
    )


def codex_prompt(repo: Path, recipient: str, message: Path) -> str:
    done_dir = signal_root(repo) / recipient / "done"
    coordinator_inbox = signal_root(repo) / "coordinator" / "inbox"
    return (
        "请自动查收并处理这封 MWA inbox 消息："
        f"{message}。"
        "要求：1. 先读取消息内容；"
        "2. 按当前 worktree 的 AGENTS.md / CLAUDE.md 和写入范围规则执行；"
        f"3. 处理完成后，将该消息移动到 {done_dir}/；"
        f"4. 如需 coordinator 决策或需要汇报结果，写入 {coordinator_inbox}/；"
        "5. 如果当前正在执行其它任务，先记录这封消息并在安全点处理。"
    )


def notify(repo: Path, config: dict, recipient: str, message: Path, mode: str | None = None) -> bool:
    session = config["session"]
    target = config.get("windows", {}).get(recipient, {}).get("target") or f"{session}:{recipient}"
    if not target_exists(target):
        return False
    text = notify_text(recipient, message)
    selected_mode = notify_mode(config, mode)
    if selected_mode == "display":
        run_tmux(["display-message", "-t", target, "-d", "8000", text])
    elif selected_mode == "send-keys":
        run_tmux(["send-keys", "-t", target, text, "Enter"])
    elif selected_mode == "codex-prompt":
        # Enter submits when Codex is idle; Tab queues the prompt when Codex is busy.
        run_tmux(["send-keys", "-t", target, codex_prompt(repo, recipient, message), "Enter", "Tab"])
    return True


def cmd_notify(args: argparse.Namespace) -> int:
    repo = repo_path(args.root)
    config = load_config(repo, args.session)
    message = Path(args.file).expanduser()
    if not message.is_absolute():
        message = signal_root(repo) / args.recipient / "inbox" / message
    if not message.exists():
        raise SystemExit(f"message not found: {message}")
    mode = notify_mode(config, args.mode)
    if notify(repo, config, args.recipient, message, mode):
        print(f"notified {args.recipient}: {message.name} ({mode})")
        return 0
    print(f"no tmux window for {args.recipient}; message remains in inbox: {message}")
    return 1


def watch_once(repo: Path, config: dict, seen: set[str], mode: str | None = None) -> int:
    count = 0
    for recipient, messages in list_inbox_messages(repo).items():
        for message in messages:
            key = str(message)
            if key in seen:
                continue
            if notify(repo, config, recipient, message, mode):
                count += 1
                seen.add(key)
    save_seen(repo, config["session"], seen)
    return count


def cmd_watch(args: argparse.Namespace) -> int:
    require_tmux()
    repo = repo_path(args.root)
    config = load_config(repo, args.session)
    mode = notify_mode(config, args.mode)
    seen = load_seen(repo, config["session"])
    while True:
        count = watch_once(repo, config, seen, mode)
        if args.once:
            print(f"notifications sent: {count}")
            return 0
        time.sleep(args.interval)


def cmd_status(args: argparse.Namespace) -> int:
    repo = repo_path(args.root)
    config = load_config(repo, args.session)
    binary = tmux_bin()
    print(f"tmux: {binary or 'not installed'}")
    print(f"session: {config['session']}")
    if binary and session_exists(config["session"]):
        print("session_state: running")
        result = run_tmux(["list-windows", "-t", config["session"], "-F", "#{window_name}"], check=False)
        if result.returncode == 0:
            print("windows:")
            for line in result.stdout.splitlines():
                print(f"- {line}")
    else:
        print("session_state: unavailable")
    if config.get("windows"):
        print("targets:")
        for recipient, window in sorted(config["windows"].items()):
            target = window.get("target") or f"{config['session']}:{recipient}"
            state = "available" if binary and target_exists(target) else "unavailable"
            print(f"- {recipient}: {target} ({state})")
    print(f"notify_mode: {notify_mode(config, None)}")
    print(f"config: {tmux_config_path(repo)}")
    print(f"seen: {seen_path(repo, config['session'])}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="report whether tmux is available")
    check.set_defaults(func=cmd_check)

    start = sub.add_parser("start", help="create or reuse a tmux session for coordinator and agents")
    start.add_argument("--root", required=True)
    start.add_argument("--topology", required=True)
    start.add_argument("--session")
    start.add_argument("--coordinator-command")
    start.add_argument("--agent-command")
    start.set_defaults(func=cmd_start)

    auto = sub.add_parser("auto", help="start tmux mode when tmux exists; otherwise fall back cleanly")
    auto.add_argument("--root", required=True)
    auto.add_argument("--topology", required=True)
    auto.add_argument("--session")
    auto.add_argument("--coordinator-command")
    auto.add_argument("--agent-command")
    auto.set_defaults(func=cmd_auto)

    attach = sub.add_parser("attach", help="attach to the configured tmux session")
    attach.add_argument("--root", required=True)
    attach.add_argument("--session")
    attach.set_defaults(func=cmd_attach)

    notify_cmd = sub.add_parser("notify", help="send one inbox notification to a recipient tmux window")
    notify_cmd.add_argument("--root", required=True)
    notify_cmd.add_argument("--session")
    notify_cmd.add_argument("--recipient", required=True)
    notify_cmd.add_argument("--file", required=True)
    notify_cmd.add_argument("--mode", choices=sorted(VALID_NOTIFY_MODES))
    notify_cmd.set_defaults(func=cmd_notify)

    watch = sub.add_parser("watch", help="watch .mwa inboxes and notify matching tmux windows")
    watch.add_argument("--root", required=True)
    watch.add_argument("--session")
    watch.add_argument("--interval", type=float, default=5.0)
    watch.add_argument("--once", action="store_true")
    watch.add_argument("--mode", choices=sorted(VALID_NOTIFY_MODES))
    watch.set_defaults(func=cmd_watch)

    status = sub.add_parser("status", help="show tmux session and notification state")
    status.add_argument("--root", required=True)
    status.add_argument("--session")
    status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
