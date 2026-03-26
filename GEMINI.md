# AI Command Center — Gemini CLI Protocol

You are a coding agent operating under the **AI Command Center** coordination system. 
This file connects you to the project's Unified Workspace.

## Mandatory Warm-Up Sequence

Your connection to the Command Center is triggered manually by the human operator.
When you see the user type exactly `[ connect hub ]`, you MUST execute the **Warm-Up Procedure** described in `SKILL.md`.

1. Open the file `SKILL.md` located in the root directory.
2. Read **Section 3. The Mandatory Warm-Up Procedure**.
3. Execute Steps 1 through 5 of the procedure. Do not skip any steps.

## Your Identity
When registering or sending heartbeats, use:
- `agent_type`: `GEMINI`
- `machine_name`: set to your hostname or a recognizable label

## Key Variables to Set
Replace these in all API calls (from SKILL.md):
- `{COMMAND_CENTER_URL}` — the URL of the running AI Command Center backend
- `{YOUR_API_KEY}` — your agent's API key (registered in the Command Center)

> Do not proceed with manual coding until the Warm-Up sequence from SKILL.md is complete.
