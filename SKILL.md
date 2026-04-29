---
name: my-worktree-agents
description: Plan and initialize project-specific multi-agent collaboration using a root coordinator, Git worktrees, per-agent AGENTS.md/CLAUDE.md/TASKS files, and a local .mwa inbox/outbox/done message bus. Use when a user asks to split a repository across multiple coding agents, coordinate agents through worktrees, set up branch agents with write scopes, create a local multi-agent workflow, or manage coordinator/agent handoffs. Always propose the topology and get user confirmation before creating worktrees or writing setup files.
---

# My Worktree Agents

## Core Rule

Never create multi-agent worktrees before producing a project-specific agent topology proposal and receiving user confirmation.

This skill has two stages:

1. **Propose**: inspect the repository and design a multi-agent topology without writing files.
2. **Initialize**: after user confirmation, create worktrees, local agent rules, task files, and `.mwa/`.

It intentionally absorbs only lightweight orchestration patterns: worktree isolation, local mailbox messages, staged task files, read-only status reports, and explicit closeout gates. It does not attempt to become a full agent runtime.

Tmux mode is auto-detected after the user confirms the topology. If tmux is installed, use tmux-enhanced mode by default. Tmux is a live-session/notifier layer over `.mwa/`; `.mwa/` remains the source of truth. If tmux is unavailable, continue with the normal file-mailbox workflow.

The bundled scripts are intentionally conservative:

- `agent_signal.py`: local mailbox operations
- `agent_memory.py`: shared memory inside `.mwa/memory/`
- `worktree_status.py`: read-only worktree status, merge recommendations, and optional topology write-scope checks
- `handoff.py`: generate a standard completion/handoff report from a worktree
- `mwa_tmux.py`: optional tmux session launcher and inbox notifier

## Stage 1: Propose

Read only. Do not modify files.

Inspect:

```bash
git status --short --untracked-files=all
git branch --show-current
git worktree list
rg --files -g 'AGENTS.md' -g 'CLAUDE.md' -g 'TASKS*.md' -g 'package.json' -g 'Cargo.toml' -g 'pyproject.toml' -g 'go.mod' -g 'pom.xml'
find . -maxdepth 2 -type d | sort
```

Produce a proposal with:

- coordinator workspace: always the project root
- proposed agents and worktree paths
- each agent's responsibility
- allowed write paths
- forbidden paths
- shared contracts that require coordinator approval
- verification commands per agent
- branch names
- risks and unresolved questions
- operator commands for signal bus status/send/done
- auto-detected tmux mode commands, with clean fallback when tmux is unavailable
- closeout rules for merging or retiring agents
- read-only worktree status command
- optional topology JSON path for write-scope checks

Use [references/proposal-template.md](references/proposal-template.md) for the proposal shape.

Stop and ask the user to confirm or adjust the topology.

## Stage 2: Initialize

After confirmation:

1. Ensure the main worktree is clean or explicitly account for dirty files.
2. Create `.mwa/<recipient>/{inbox,outbox,done}` for coordinator and all agents.
3. Create `.mwa/memory/{shared.md,decisions.md,glossary.md,proposals/}`.
4. Create each worktree from the chosen base branch.
5. Write root `TASKS.md`; write root `AGENTS.md` and `CLAUDE.md` only when `--write-root-docs` is passed.
6. Write each worktree's local `AGENTS.md`, `CLAUDE.md`, and `TASKS_<AGENT>.md`.
7. Add or confirm `.gitignore` entries for local coordination artifacts.
8. Run tmux auto-detection. If tmux is installed, start the enhanced tmux session; otherwise keep the normal `.mwa/` workflow.
9. Mark local worktree `CLAUDE.md` as `skip-worktree` when it differs from the tracked root version.
10. Report startup instructions for each agent.

For repeatable scaffolding, create a topology JSON and run:

```bash
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/scaffold_multi_agent.py \
  --repo <repo-root> \
  --topology <confirmed-topology.json>
```

See [references/topology-json.md](references/topology-json.md).

Default behavior is non-destructive:

- existing worktree files are not overwritten unless `--force` is passed
- existing branches/worktrees are reused when present
- root `AGENTS.md` and `CLAUDE.md` are not created by the scaffold script unless explicit project policy calls for it
- `--write-root-docs` creates or updates a marked `<!-- MWA:BEGIN -->` / `<!-- MWA:END -->` coordinator block in root `AGENTS.md` and `CLAUDE.md`
- repeated `--write-root-docs` runs replace the marked block instead of appending duplicates

## Signal Bus Protocol

Use a local, ignored mailbox:

```text
.mwa/
  coordinator/{inbox,outbox,done}
  agent-name/{inbox,outbox,done}
```

Rules:

- every agent checks its inbox before starting, resuming, and handing off
- coordinator checks `.mwa/coordinator/inbox/` before working and before final responses
- sender writes to the recipient's `inbox/`
- receiver moves handled messages to its own `done/`
- sender may keep a copy in its own `outbox/`

Use [references/signal-protocol.md](references/signal-protocol.md) for message templates.

Use the bundled helper for routine mailbox operations:

```bash
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/agent_signal.py inbox --root <repo-root> --recipient coordinator
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/agent_signal.py send --root <repo-root> --from coordinator --to agent-x --topic "decision" --body "..."
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/agent_signal.py unread --root <repo-root>
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/agent_signal.py nudge --root <repo-root> --from coordinator --to agent-x
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/agent_signal.py done --root <repo-root> --recipient coordinator --file <message-file>
```

## Optional Tmux Mode

Use tmux mode automatically after topology confirmation when tmux is installed. Do not make tmux a hard dependency.

Concept:

```text
.mwa/ mailbox = durable protocol and audit trail
tmux         = live agent sessions and notification transport
```

Useful commands:

```bash
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/mwa_tmux.py check
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/mwa_tmux.py auto \
  --root <repo-root> \
  --topology <confirmed-topology.json> \
  --session <session-name> \
  --coordinator-command 'codex resume agent-master' \
  --agent-command 'codex resume {agent}'
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/mwa_tmux.py watch --root <repo-root> --session <session-name>
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/mwa_tmux.py status --root <repo-root> --session <session-name>
```

`auto` starts tmux mode if tmux exists and otherwise exits cleanly with the normal file-mailbox workflow. `start` requires tmux and fails if it is missing. Both write `.mwa/tmux.json` when tmux starts. `watch` scans `.mwa/*/inbox/` and uses tmux `display-message` by default to notify the matching recipient target without typing into Codex input. Agents must still read inbox files and move handled messages to `done/`.

Notification modes:

- `display`: default; shows a tmux status message and does not modify the active input line.
- `codex-prompt`: sends a structured instruction into the target Codex session to read and process the specific inbox file, move it to `done/`, and reply if needed. It also sends Tab after Enter so Codex queues the prompt when it is busy.
- `send-keys`: legacy strong prompt; types the notification into the target pane and presses Enter.

`.mwa/tmux.json` may point recipients to different tmux sessions/windows:

```json
{
  "session": "project-mwa-watch",
  "notify_mode": "codex-prompt",
  "windows": {
    "coordinator": {
      "target": "project-coordinator:0"
    },
    "agent-api": {
      "target": "project-agent-api:0"
    }
  }
}
```

If tmux is missing or a session/window is not available, leave the message in the inbox and continue with file-mailbox coordination.

## Shared Memory

Shared memory lives inside the signal bus:

```text
.mwa/memory/
  shared.md
  decisions.md
  glossary.md
  proposals/
```

Rules:

- all agents may read memory before major planning
- only coordinator should append directly to `shared.md`, `decisions.md`, and `glossary.md`
- branch agents propose updates through `agent_memory.py propose`
- coordinator accepts proposals with `agent_memory.py accept`

Commands:

```bash
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/agent_memory.py read --root <repo-root>
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/agent_memory.py propose --root <repo-root> --from agent-x --target decisions --topic "runtime boundary" --body "..."
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/agent_memory.py accept --root <repo-root> --file <proposal-file>
```

## Agent File Rules

Root coordinator files:

```text
AGENTS.md
CLAUDE.md
TASKS.md
```

Per-worktree local files:

```text
.worktrees/agent-x/AGENTS.md
.worktrees/agent-x/CLAUDE.md
.worktrees/agent-x/TASKS_X.md
```

`AGENTS.md` and `CLAUDE.md` should be content-identical within each workspace unless the user asks otherwise.

Per-agent files must clearly state:

- role and worktree path
- allowed write scope
- forbidden write scope
- coordination rules
- signal bus inbox path
- task file rules
- shared-contract rules
- verification commands

Each `TASKS_<AGENT>.md` should keep these phases visible:

- Inbox
- Active Task
- Discover
- Plan
- Implement
- Verify
- Blockers
- Handoff

Use [references/agent-file-templates.md](references/agent-file-templates.md).

## Merge And Closeout

When collecting work:

1. Check each worktree status.
2. Identify local-only files versus source changes.
3. Preserve local `AGENTS.md`, `CLAUDE.md`, `TASKS_*.md`, and reports.
4. Merge or cherry-pick only source changes intended for main.
5. Re-run shared verification.
6. Keep main clean.
7. Move handled coordinator inbox messages to `done/`.

Never run destructive Git operations against a worktree with unknown local changes. Back up local coordination files before any reset/rebase.

For long-running teams, keep a lightweight status loop:

```bash
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/agent_signal.py status --root <repo-root>
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/agent_signal.py unread --root <repo-root>
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/worktree_status.py --root <repo-root> --topology <confirmed-topology.json>
git worktree list
```

If an agent is retired, record why in `TASKS.md`, preserve its local report if useful, and remove the worktree only after its source changes are either merged, intentionally dropped, or archived.

Treat `worktree_status.py` as an audit aid only. It reports dirty files, local-only files, ahead/behind counts, and diff stats; it does not merge, reset, delete, or resolve conflicts.

Before asking coordinator to integrate work, branch agents can generate a handoff:

```bash
python3 /Users/sun/.codex/skills/my-worktree-agents/scripts/handoff.py \
  --worktree <worktree-path> \
  --agent agent-x \
  --base <base-branch-or-ref>
```

The handoff output can be sent through `agent_signal.py send --body-file`.
