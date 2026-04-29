# Proposal Template

Use this shape in Stage 1. Do not create files before the user confirms.

```markdown
**Multi-Agent Topology Proposal**

Base branch:
- `<branch>`

Coordinator:
- Workspace: `<repo-root>`
- Responsibilities:
  - architecture and shared contracts
  - cross-agent decisions
  - merge/rebase/cherry-pick
  - packaging/release/final verification

Agents:

### agent-<name>
- Worktree: `.worktrees/agent-<name>`
- Branch: `feat/agent-<name>`
- Responsibilities:
  - ...
- Allowed write paths:
  - ...
- Forbidden paths:
  - ...
- Shared contracts needing coordinator:
  - ...
- Verification:
  - ...
- Risks:
  - ...

Signal bus:
- `.mwa/coordinator/inbox/`
- `.mwa/agent-<name>/inbox/`
- `.mwa/memory/shared.md`
- `.mwa/memory/decisions.md`

Auto-detected tmux mode:
- After topology confirmation, run `mwa_tmux.py auto`.
- If tmux is installed, use live sessions by default.
- If tmux is unavailable, continue with the normal `.mwa/` mailbox workflow.
- Session: `<project>-mwa`
- Coordinator window: `coordinator`
- Agent windows: `agent-<name>`
- Watcher: notifies windows when `.mwa/*/inbox/` receives new messages.

Operator commands:
- Send: `python3 <skill>/scripts/agent_signal.py send --root <repo-root> --from coordinator --to agent-<name> --topic "<topic>" --body-file <file>`
- Inbox: `python3 <skill>/scripts/agent_signal.py inbox --root <repo-root> --recipient coordinator`
- Unread: `python3 <skill>/scripts/agent_signal.py unread --root <repo-root>`
- Nudge: `python3 <skill>/scripts/agent_signal.py nudge --root <repo-root> --from coordinator --to agent-<name>`
- Done: `python3 <skill>/scripts/agent_signal.py done --root <repo-root> --recipient coordinator --file <message-file>`
- Worktree audit: `python3 <skill>/scripts/worktree_status.py --root <repo-root> --topology <confirmed-topology.json>`
- Handoff: `python3 <skill>/scripts/handoff.py --worktree <worktree-path> --agent agent-<name> --base <base-ref>`
- Memory read: `python3 <skill>/scripts/agent_memory.py read --root <repo-root>`
- Memory propose: `python3 <skill>/scripts/agent_memory.py propose --root <repo-root> --from agent-<name> --target shared --topic "<topic>" --body "..."`
- Tmux check: `python3 <skill>/scripts/mwa_tmux.py check`
- Tmux auto: `python3 <skill>/scripts/mwa_tmux.py auto --root <repo-root> --topology <confirmed-topology.json> --session <project>-mwa`
- Tmux start: `python3 <skill>/scripts/mwa_tmux.py start --root <repo-root> --topology <confirmed-topology.json> --session <project>-mwa`
- Tmux watch: `python3 <skill>/scripts/mwa_tmux.py watch --root <repo-root> --session <project>-mwa`
- Tmux status: `python3 <skill>/scripts/mwa_tmux.py status --root <repo-root> --session <project>-mwa`

Gitignore additions:
- `.worktrees/`
- `.mwa/`
- `TASKS_*.md`
- `*-REPORT.md`

Please confirm, remove, rename, or adjust the agents before I create worktrees.
```
}
```

Fields:

- `base_branch`: branch/ref used when creating worktrees
- `worktree_root`: default `.worktrees`
- `signal_root`: default `.mwa`
- `agents[].name`: directory name and signal bus key
- `agents[].branch`: branch name; default `feat/<name>` if omitted
- `agents[].role`: display title in agent files
- `allowed_paths`, `forbidden_paths`, `verification`: rendered into local agent files

The script creates files only after the topology has been confirmed by the user.
