# Feature List

Lightweight local coordination for a root coordinator plus multiple branch agents.

This skill uses Git worktrees, per-agent instruction files, local task files, a file-based signal bus, and shared memory under `.mwa/`. It is intentionally not a full runtime, MCP server, or automatic merge system. Tmux mode is auto-detected: when tmux is installed, MWA can start live sessions and notify inboxes by default.

## Core Workflow

1. Inspect the repository.
2. Propose a project-specific multi-agent topology.
3. Wait for user confirmation.
4. Initialize worktrees, agent files, task files, signal bus, and shared memory.
5. Coordinate through local messages, handoffs, and read-only status reports.
6. Let the coordinator decide integration and closeout.
7. Auto-detect tmux. If installed, run coordinator/agents in tmux and notify them when new inbox messages arrive.

## Created Structure

```text
.worktrees/<agent>/
  AGENTS.md
  CLAUDE.md
  TASKS_<AGENT>.md

.mwa/
  coordinator/{inbox,outbox,done}
  <agent>/{inbox,outbox,done}
  memory/
    shared.md
    decisions.md
    glossary.md
    proposals/
```

When `--write-root-docs` is passed, root `AGENTS.md` and `CLAUDE.md` receive a coordinator block:

```text
<!-- MWA:BEGIN -->
...
<!-- MWA:END -->
```

The block is replaced on repeated runs.

## Scripts

### `scaffold_multi_agent.py`

Creates the confirmed worktree setup.

```bash
python3 scripts/scaffold_multi_agent.py --repo <repo-root> --topology <topology.json>
python3 scripts/scaffold_multi_agent.py --repo <repo-root> --topology <topology.json> --write-root-docs
```

Default behavior is non-destructive. Existing agent files are preserved unless `--force` is passed.
Root `AGENTS.md` and `CLAUDE.md` are updated only with `--write-root-docs`.

### `agent_signal.py`

Local mailbox operations.

```bash
python3 scripts/agent_signal.py status --root <repo-root>
python3 scripts/agent_signal.py unread --root <repo-root>
python3 scripts/agent_signal.py send --root <repo-root> --from coordinator --to agent-x --topic "decision" --body "..."
python3 scripts/agent_signal.py nudge --root <repo-root> --from coordinator --to agent-x
python3 scripts/agent_signal.py reply --root <repo-root> --from agent-x --file <message-file> --body "..."
python3 scripts/agent_signal.py done --root <repo-root> --recipient coordinator --file <message-file>
python3 scripts/agent_signal.py archive --root <repo-root> --recipient coordinator
```

### `agent_memory.py`

Shared memory stored inside `.mwa/memory/`.

```bash
python3 scripts/agent_memory.py init --root <repo-root>
python3 scripts/agent_memory.py read --root <repo-root>
python3 scripts/agent_memory.py propose --root <repo-root> --from agent-x --target decisions --topic "<topic>" --body "..."
python3 scripts/agent_memory.py list --root <repo-root>
python3 scripts/agent_memory.py accept --root <repo-root> --file <proposal-file>
python3 scripts/agent_memory.py append --root <repo-root> --from coordinator --target shared --body "..."
```

Rules:

- All agents may read shared memory.
- Branch agents propose memory changes.
- The coordinator accepts proposals or appends directly.

### `worktree_status.py`

Read-only worktree audit and merge planning.

```bash
python3 scripts/worktree_status.py --root <repo-root>
python3 scripts/worktree_status.py --root <repo-root> --topology <topology.json>
python3 scripts/worktree_status.py --root <repo-root> --topology <topology.json> --json
```

Reports:

- branch
- dirty state
- ahead / behind
- source dirty files
- local-only dirty files
- diff stat
- merge recommendation
- write-scope violations when topology is provided

Merge recommendations are advisory only. The script never merges, resets, deletes, or resolves conflicts.

### `handoff.py`

Generates a standard completion report from a worktree.

```bash
python3 scripts/handoff.py --worktree <worktree-path> --agent agent-x --base <base-ref>
python3 scripts/handoff.py --worktree <worktree-path> --agent agent-x --base <base-ref> --output handoff.md
```

The report can be edited and sent with:

```bash
python3 scripts/agent_signal.py send --root <repo-root> --from agent-x --to coordinator --topic "completed <task>" --body-file handoff.md --outbox
```

### `mwa_tmux.py`

Optional tmux live-session support.

```bash
python3 scripts/mwa_tmux.py check
python3 scripts/mwa_tmux.py auto --root <repo-root> --topology <topology.json> --session <name>
python3 scripts/mwa_tmux.py start --root <repo-root> --topology <topology.json> --session <name>
python3 scripts/mwa_tmux.py watch --root <repo-root> --session <name>
python3 scripts/mwa_tmux.py notify --root <repo-root> --recipient agent-x --file <message-file>
python3 scripts/mwa_tmux.py status --root <repo-root> --session <name>
```

Rules:

- Use automatically after topology confirmation when tmux is installed.
- `.mwa/` remains the durable source of truth.
- Tmux notifications do not mark messages done.
- Tmux notifications default to `display`, not `send-keys`, so they do not type into Codex input.
- Use `codex-prompt` when you want tmux to drive Codex agents to read and process inbox messages automatically.
- Agents still read inbox files and move handled messages to `done/`.
- Recipients may point to different tmux sessions/windows through `.mwa/tmux.json` `windows.<recipient>.target`.
- If tmux is unavailable, `auto` exits cleanly and the workflow continues with `agent_signal.py`.

## Topology JSON

Example:

```json
{
  "base_branch": "main",
  "worktree_root": ".worktrees",
  "signal_root": ".mwa",
  "agents": [
    {
      "name": "agent-frontend",
      "branch": "feat/agent-frontend",
      "role": "Frontend agent",
      "responsibilities": ["UI implementation"],
      "allowed_paths": ["frontend/", "src/ui/"],
      "forbidden_paths": ["backend/", "infra/"],
      "verification": ["npm test", "npm run build"]
    }
  ]
}
```

## Agent Task Stages

Generated `TASKS_<AGENT>.md` files use:

- Inbox
- Active Task
- Discover
- Plan
- Implement
- Verify
- Blockers
- Handoff

## Closeout Rules

- Coordinator checks inbox and worktree status before final reporting.
- Branch agents send handoffs before integration.
- Local task/report files are preserved but not merged to main by default.
- Write-scope violations require manual coordinator review.
- Dirty worktrees are not reset or deleted automatically.
