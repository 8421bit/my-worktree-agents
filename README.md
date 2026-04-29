# My Worktree Agents

`my-worktree-agents` is a Codex skill for coordinating multiple coding agents in one project using Git worktrees.

It sets up a root coordinator, branch-agent worktrees, local task files, a `.mwa/` mailbox, shared memory, handoff reports, and read-only worktree status checks.

It is intentionally lightweight. It is not a full agent runtime, MCP server, or automatic merge system.

Tmux support is auto-detected. When tmux is installed, MWA should use tmux-enhanced mode by default: start coordinator/agent tmux windows and notify those windows when new `.mwa/` inbox messages arrive. Without tmux, the normal file-mailbox workflow remains unchanged.

MWA can notify either one shared tmux session or multiple independent tmux sessions. Each recipient can point to its own tmux target through `.mwa/tmux.json`, for example `project-coordinator:0` and `project-agent-runtime:0`. Notifications default to tmux `display-message`, so MWA does not type into an active Codex input box. When you want agents to automatically read and act on inbox messages, use `notify_mode: "codex-prompt"`.

## Features

- Propose a project-specific multi-agent topology before creating anything.
- Initialize one Git worktree per branch agent.
- Generate local `AGENTS.md`, `CLAUDE.md`, and `TASKS_<AGENT>.md` files.
- Optionally update root `AGENTS.md` and `CLAUDE.md` with a marked coordinator block.
- Use `.mwa/<recipient>/{inbox,outbox,done}` as a local file mailbox.
- Store shared memory in `.mwa/memory/`.
- Let branch agents propose memory updates and coordinator accept them.
- Generate handoff reports from worktrees.
- Audit worktree status, ahead/behind, dirty files, local-only files, and write-scope violations.
- Keep all merge recommendations advisory and read-only.
- Auto-detect tmux and run coordinator/agents in tmux when available.

## What Is MWA?

MWA is a local multi-agent coordination skill for Codex. It helps a root coordinator split one repository into multiple Git worktree agents, give each agent clear write boundaries, and coordinate work through local files.

MWA is useful when a project has parallelizable work such as frontend/backend splits, runtime adapters, documentation, tests, or independent feature areas. The coordinator remains in the main repository, while branch agents work in `.worktrees/<agent>/`.

## Installation

Install from GitHub with Codex's skill installer:

```text
Install the Codex skill from https://github.com/8421bit/my-worktree-agents
```

Or clone it into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/8421bit/my-worktree-agents.git ~/.codex/skills/my-worktree-agents
```

Restart Codex after installation if the skill list has already been loaded.

## How To Enable

From a project root, ask Codex to use the skill:

```text
请使用 my-worktree-agents 为当前项目设计一个多 agent worktree 协作方案。
```

MWA has two normal steps:

1. Codex proposes a project-specific topology first.
2. After you confirm, Codex initializes `.worktrees/`, `.mwa/`, agent instructions, and task files.

If `tmux` is installed, MWA uses tmux-enhanced mode automatically after initialization. If `tmux` is not installed, it uses the normal `.mwa/` file mailbox.

## Usage Examples

Send one of these instructions to Codex from a project root.

### Plan A Multi-Agent Workspace

```text
请使用 my-worktree-agents 分析当前代码库，设计一个多 agent worktree 协作方案。先只提出 topology、每个 agent 的职责、写入范围、风险和验证命令，不要创建文件，等我确认后再初始化。
```

English equivalent:

```text
Use my-worktree-agents to inspect this repository and propose a multi-agent worktree topology. Do not create files yet. Include each agent's responsibility, write scope, forbidden paths, risks, and verification commands. Wait for my confirmation.
```

### Initialize After Approval

```text
我确认这个 MWA topology。请开始初始化 worktrees、.mwa 信箱、每个 agent 的 AGENTS.md / CLAUDE.md / TASKS 文件；如果检测到 tmux，就自动启用 tmux 增强模式。
```

### Start Or Resume Tmux Enhanced Mode

```text
请使用 MWA 检测当前项目是否可以启用 tmux 增强模式。如果已安装 tmux，请启动 coordinator 和各 agent 的 tmux windows，并开启 inbox watcher；如果没有 tmux，就继续使用 .mwa 文件信箱。
```

### Send Work To A Branch Agent

```text
请通过 MWA 给 agent-runtime 发消息：继续处理 runtime adapter 产品化，但只能修改它自己的 worktree 和允许写入范围。发送后如果 tmux watcher 可用，请通知它查收 inbox。
```

### Check Status

```text
请使用 MWA 检查所有 agent 的 inbox、worktree dirty 状态、ahead/behind、写入范围违规风险，并告诉我哪些可以合并、哪些需要继续处理。
```

### Collect A Handoff

```text
请使用 MWA 收集 agent-frontend 的 handoff，总结它改了哪些文件、验证结果、残留风险，然后判断是否可以由 coordinator 合并回主工作区。
```

### Close Out Agents

```text
请使用 MWA 收口当前多 agent 工作区：保留有价值的 handoff/report，确认需要合并的源码改动，忽略本地 agent 上下文文件，最后让主工作区回到 clean 状态。
```

## Structure

```text
my-worktree-agents/
  SKILL.md
  agents/openai.yaml
  references/
  scripts/
```

Project-local coordination state is created under:

```text
.mwa/
  coordinator/{inbox,outbox,done}
  <agent>/{inbox,outbox,done}
  memory/
    shared.md
    decisions.md
    glossary.md
    proposals/
```

## Main Scripts

```bash
python3 scripts/scaffold_multi_agent.py --repo <repo-root> --topology <topology.json>
python3 scripts/scaffold_multi_agent.py --repo <repo-root> --topology <topology.json> --write-root-docs
python3 scripts/agent_signal.py status --root <repo-root>
python3 scripts/agent_memory.py read --root <repo-root>
python3 scripts/worktree_status.py --root <repo-root> --topology <topology.json>
python3 scripts/handoff.py --worktree <worktree-path> --agent <agent-name> --base <base-ref>
python3 scripts/mwa_tmux.py check
python3 scripts/mwa_tmux.py auto --root <repo-root> --topology <topology.json> --session <name>
python3 scripts/mwa_tmux.py start --root <repo-root> --topology <topology.json> --session <name>
python3 scripts/mwa_tmux.py watch --root <repo-root> --session <name>
```

`--write-root-docs` creates or updates a coordinator section in root `AGENTS.md` and `CLAUDE.md` using:

```text
<!-- MWA:BEGIN -->
...
<!-- MWA:END -->
```

Repeated runs replace the marked block rather than appending duplicates.

## Topology Example

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

## Safety Model

- The skill must propose topology and wait for user confirmation before creating worktrees.
- Existing agent files are preserved unless `--force` is passed.
- Root `AGENTS.md` and `CLAUDE.md` are not changed unless `--write-root-docs` is passed.
- Branch agents should not write outside their allowed paths.
- Shared memory files are coordinator-owned; branch agents submit proposals.
- Worktree status and merge planning are read-only.
- Dirty worktrees are not reset or deleted automatically.

## Optional Tmux Mode

MWA auto-detects tmux. After the user confirms the multi-agent topology and worktrees are initialized, run `mwa_tmux.py auto`. If tmux exists, it starts the enhanced live-session workflow; if tmux is missing, it exits cleanly and keeps the normal `.mwa/` mailbox workflow.

```bash
python3 scripts/mwa_tmux.py check
python3 scripts/mwa_tmux.py auto \
  --root <repo-root> \
  --topology <topology.json> \
  --session project-mwa \
  --coordinator-command 'codex resume agent-master' \
  --agent-command 'codex resume {agent}'

python3 scripts/mwa_tmux.py watch --root <repo-root> --session project-mwa
```

The watcher scans `.mwa/*/inbox/` and displays a short prompt in the matching tmux window:

```text
MWA inbox: <message>. Please read .mwa/<recipient>/inbox, handle the message, and move it to done.
```

The mailbox remains authoritative. Tmux only provides live processes and notifications.

Notification modes:

```bash
python3 scripts/mwa_tmux.py watch --root <repo-root> --session project-mwa --mode display
python3 scripts/mwa_tmux.py watch --root <repo-root> --session project-mwa --mode codex-prompt
python3 scripts/mwa_tmux.py watch --root <repo-root> --session project-mwa --mode send-keys
```

- `display`: default; shows a tmux status message and does not touch the shell/Codex input.
- `codex-prompt`: sends a structured instruction into the target Codex session to read, process, move the message to `done/`, and reply when needed. It also sends Tab after Enter so Codex queues the prompt when it is busy.
- `send-keys`: legacy strong prompt; types the notification into the target pane and presses Enter.

### Multiple Tmux Sessions

If you want two iTerm2 panes to stay fixed independently, run coordinator and agents in separate tmux sessions, then point each recipient at the right tmux target:

```json
{
  "session": "project-mwa-watch",
  "notify_mode": "codex-prompt",
  "windows": {
    "coordinator": {
      "target": "project-coordinator:0"
    },
    "agent-runtime": {
      "target": "project-agent-runtime:0"
    }
  }
}
```

The same shape can be declared in topology JSON before running `mwa_tmux.py auto`:

```json
{
  "tmux": {
    "session": "project-mwa-watch",
    "notify_mode": "codex-prompt",
    "targets": {
      "coordinator": {
        "target": "project-coordinator:0"
      },
      "agent-runtime": {
        "target": "project-agent-runtime:0"
      }
    }
  }
}
```

Then run:

```bash
python3 scripts/mwa_tmux.py watch --root <repo-root> --session project-mwa-watch
```

`watch` sends notifications to each configured `target`; it no longer requires all recipients to live in one tmux session.
