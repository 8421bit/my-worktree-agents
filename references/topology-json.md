# Topology JSON

`scripts/scaffold_multi_agent.py` expects a confirmed topology JSON:

```json
{
  "base_branch": "main",
  "worktree_root": ".worktrees",
  "signal_root": ".mwa",
  "tmux": {
    "session": "project-mwa",
    "notify_mode": "codex-prompt",
    "coordinator_command": "codex resume agent-master",
    "agent_command": "codex resume {agent}",
    "targets": {
      "coordinator": {
        "target": "project-coordinator:0"
      },
      "agent-frontend": {
        "target": "project-agent-frontend:0"
      }
    }
  },
  "coordinator": {
    "name": "coordinator",
    "responsibilities": [
      "architecture",
      "shared contracts",
      "merge and release"
    ]
  },
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

Fields:

- `base_branch`: branch/ref used when creating worktrees
- `worktree_root`: default `.worktrees`
- `signal_root`: default `.mwa`
- `tmux`: optional live-session settings used by auto-detected tmux mode
- `tmux.session`: tmux session name
- `tmux.notify_mode`: `display` by default; use `codex-prompt` to drive Codex agents to read/process inbox messages automatically; use `send-keys` only when you intentionally want raw notifications typed into panes
- `tmux.coordinator_command`: command for the coordinator window
- `tmux.agent_command`: command template for agent windows; supports `{agent}`, `{recipient}`, `{repo}`, `{worktree}`
- `tmux.targets`: optional recipient-to-target mapping; use it when coordinator and agents run in separate tmux sessions
- `agents[].name`: directory name and signal bus key
- `agents[].branch`: branch name; default `feat/<name>` if omitted
- `agents[].role`: display title in agent files
- `allowed_paths`, `forbidden_paths`, `verification`: rendered into local agent files
- `agents[].tmux_command`: optional per-agent tmux command override
- `agents[].tmux_target`: optional per-agent target override, such as `project-agent-api:0`

The script creates files only after the topology has been confirmed by the user.

By default, the script preserves existing worktree-local `AGENTS.md`, `CLAUDE.md`, and `TASKS_*.md`.
Pass `--force` only when the user explicitly wants those files regenerated.

Root docs:

```bash
python3 <skill>/scripts/scaffold_multi_agent.py --repo <repo-root> --topology <confirmed-topology.json> --write-root-docs
```

This creates or updates a marked MWA coordinator block in root `AGENTS.md` and `CLAUDE.md`.
It is off by default.

Closeout/status audit:

```bash
python3 <skill>/scripts/worktree_status.py --root <repo-root>
python3 <skill>/scripts/worktree_status.py --root <repo-root> --topology <confirmed-topology.json>
python3 <skill>/scripts/worktree_status.py --root <repo-root> --topology <confirmed-topology.json> --json
```

This report is read-only and intended to guide coordinator merge decisions. With a topology file, it also checks changed files against each agent's `allowed_paths` and `forbidden_paths`.

Agent handoff:

```bash
python3 <skill>/scripts/handoff.py --worktree <worktree-path> --agent <agent-name> --base <base-ref> --output <handoff-file.md>
```

The handoff report is safe to edit before sending to coordinator.

Shared memory is initialized under `.mwa/memory/` by the scaffold script. It is local coordination state, not a repository deliverable unless the user explicitly asks to commit it elsewhere.
