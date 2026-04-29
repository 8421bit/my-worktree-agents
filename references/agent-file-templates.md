# Agent File Templates

Use these sections in each worktree's `AGENTS.md` and `CLAUDE.md`.

````markdown
# Agent: <Role>

## Workspace

You are in:

```text
<repo-root>/.worktrees/agent-<name>
```

This is a branch-agent worktree. The coordinator works in:

```text
<repo-root>
```

## Responsibilities

- ...

## Allowed Writes

```text
...
```

## Forbidden Writes

```text
...
```

## Signal Bus

All agents use:

```text
<repo-root>/.mwa/
```

Your inbox:

```text
<repo-root>/.mwa/agent-<name>/inbox/
```

Rules:

- Check your inbox before starting work, resuming work, and handing off.
- Read `.mwa/memory/shared.md` and `.mwa/memory/decisions.md` before major planning.
- Send coordinator messages to `<repo-root>/.mwa/coordinator/inbox/`.
- Send other agent messages to that agent's `inbox/`.
- Move handled messages to your own `done/`.
- Keep a copy in your own `outbox/` when useful.
- Use `agent_signal.py inbox/send/reply/done/status` when available.
- Use `agent_memory.py propose` to request memory updates; do not directly edit shared memory unless coordinator authorizes it.

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

- Keep local `TASKS_<NAME>.md` and `*-REPORT.md` only in this worktree.
- Do not merge local task/report files to main.
- Long-lived backlog items go through coordinator.
- Keep your task file updated by stage: Discover, Plan, Implement, Verify, Handoff.

## Task File Stages

```markdown
## Inbox
## Active Task
## Discover
## Plan
## Implement
## Verify
## Blockers
## Handoff
```

## Shared Memory

Read before major planning:

```bash
python3 <skill>/scripts/agent_memory.py read --root <repo-root>
```

Propose durable facts or decisions:

```bash
python3 <skill>/scripts/agent_memory.py propose --root <repo-root> --from <agent-name> --target shared --topic "<topic>" --body "..."
```

Generate a draft when ready:

```bash
python3 <skill>/scripts/handoff.py --worktree <worktree-path> --agent <agent-name> --base <base-ref>
```

Then send the edited report to coordinator:

```bash
python3 <skill>/scripts/agent_signal.py send --root <repo-root> --from <agent-name> --to coordinator --topic "completed <task>" --body-file <handoff-file.md> --outbox
```

Coordinator may run:

```bash
python3 <skill>/scripts/worktree_status.py --root <repo-root> --topology <confirmed-topology.json>
```
```

## Verification

```bash
...
```
````
