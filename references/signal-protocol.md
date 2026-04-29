# Signal Protocol

Local message bus:

```text
.mwa/<recipient>/inbox/
.mwa/<recipient>/outbox/
.mwa/<recipient>/done/
.mwa/memory/
```

Filename convention:

```text
YYYYMMDD-HHMMSS-<from>-to-<to>-<topic>.md
```

Prefer the helper script for routine operations:

```bash
python3 <skill>/scripts/agent_signal.py status --root <repo-root>
python3 <skill>/scripts/agent_signal.py unread --root <repo-root>
python3 <skill>/scripts/agent_signal.py inbox --root <repo-root> --recipient coordinator
python3 <skill>/scripts/agent_signal.py send --root <repo-root> --from coordinator --to agent-api --topic "contract decision" --body "..."
python3 <skill>/scripts/agent_signal.py nudge --root <repo-root> --from coordinator --to agent-api
python3 <skill>/scripts/agent_signal.py reply --root <repo-root> --from coordinator --file <message-file> --body "..."
python3 <skill>/scripts/agent_signal.py done --root <repo-root> --recipient coordinator --file <message-file>
python3 <skill>/scripts/agent_signal.py archive --root <repo-root> --recipient coordinator
```

Shared memory:

```text
.mwa/memory/shared.md      # coordinator-approved facts
.mwa/memory/decisions.md   # coordinator-approved decisions
.mwa/memory/glossary.md    # shared project terms
.mwa/memory/proposals/     # branch-agent proposals
```

Memory commands:

```bash
python3 <skill>/scripts/agent_memory.py read --root <repo-root>
python3 <skill>/scripts/agent_memory.py propose --root <repo-root> --from agent-api --target shared --topic "important fact" --body "..."
python3 <skill>/scripts/agent_memory.py list --root <repo-root>
python3 <skill>/scripts/agent_memory.py accept --root <repo-root> --file <proposal-file>
python3 <skill>/scripts/agent_memory.py append --root <repo-root> --from coordinator --target decisions --body "..."
```

General message:

```markdown
# <Topic>

From: <sender>
To: <recipient>
Date: YYYY-MM-DD
Status: unread

Summary:
...

Request:
...

Context:
...

Expected response:
...
```

Blocked coordinator message:

```markdown
# Blocked: <short topic>

[BLOCKED -> coordinator]
From: <agent>
To: coordinator
Date: YYYY-MM-DD
Status: unread

Summary:
...

Needs:
...

Files affected:
...

Decision required:
...
```

Completion message:

```markdown
# Completed: <short topic>

From: <agent>
To: coordinator
Date: YYYY-MM-DD
Status: unread

Summary:
...

Changed files:
...

Validation:
...

Residual risk:
...
```

Coordinator closeout message:

```markdown
# Closeout: <agent or phase>

From: coordinator
To: <agent>
Date: YYYY-MM-DD
Status: unread

Decision:
...

Source changes:
...

Local-only files to preserve:
...

Next:
...
```
