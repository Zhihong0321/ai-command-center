---
name: AI Command Center
description: Full protocol for the AI Command Center. Defines the mandatory Warm-Up Procedure, session rules, note-taking, submission schemas, and task claiming.
---

# AI Command Center — Agent SKILL

## 1. Purpose

The **AI Command Center** is the single source of truth for all AI coding agents and the human operator working across multiple GitHub repos. Its purpose is to:

- **Provide a Unified Workspace** — Central hub of info, notes, progress, and tasks.
- **Prevent overlap** — only one agent can claim a task at a time.
- **Give every agent full context** — before starting work on a repo, check this center to understand the current state, history, and what other agents have done.
- **Record everything** — all work, questions, analysis, bugs, and notes are written here so future agents (and humans) can pick up seamlessly.

### 📚 API Documentation
The Command Center provides interactive API documentation (Swagger UI) at:
`{COMMAND_CENTER_URL}/docs`
Refer to this for detailed endpoint schemas, status codes, and manual testing.

---

## 2. What You Can Do Here

| Feature | What it means for you |
|---|---|
| **Dashboard** | See all active agents, all repos, recent activity, and active broadcasts in one call. |
| **Repo Registry** | Look up any registered project — its local directory path, GitHub URL, and freshness. |
| **Task Board** | See all tasks per repo, their status, and who owns them. Create new tasks. |
| **Task Claiming** | Lock a task to yourself. |
| **Activity Feed** | Post your progress, blockers, questions, analysis results, and completion notes. |
| **Notes** | Post timestamped notes that serve as permanent record for future agents. |

---

## 3. The Mandatory Warm-Up Procedure (Trigger: `[ connect hub ]`)

> **CRITICAL RULE:** The AI Command Center runs on a manual-trigger protocol. You must wait for the human operator to type the command `[ connect hub ]`. Once you see this command in your conversation, **you must execute this exact sequence.**

When you see the human say `[ connect hub ]`, run these steps *in order*:

### Step 1 — Announce yourself (Ping the Hub)
Let the Command Center know you are online.
```
POST {COMMAND_CENTER_URL}/api/agents/heartbeat
X-API-Key: {YOUR_API_KEY}
Body: { "status": "WORKING", "machine_name": "your-machine-name" }
```

### Step 2 — Read Human Broadcasts
The human operator can issue global instructions. You must read them.
```
GET {COMMAND_CENTER_URL}/api/broadcasts?active_only=true
X-API-Key: {YOUR_API_KEY}
```

### Step 3 — Discover & Claim a Task (If none assigned)
If the human told you exactly what to do, skip to Step 4. Otherwise, query for an open task for your repository:
```
GET {COMMAND_CENTER_URL}/api/tasks?repo={repo_name}&status=OPEN&limit=5
X-API-Key: {YOUR_API_KEY}
```
*Note: The returned task includes a `repo.local_path`. This is the exact folder on disk you MUST switch to before working.*

Claim the highest-priority task:
```
POST {COMMAND_CENTER_URL}/api/tasks/{task_id}/claim
X-API-Key: {YOUR_API_KEY}
```
*(If you receive a `409 Conflict`, pick the next task in the list).*

### Step 4 — Read History (Crucial Context)
You must understand what the *previous* AI agent did so you don't break their work.
```
GET {COMMAND_CENTER_URL}/api/activity?repo={repo_name}&limit=10
X-API-Key: {YOUR_API_KEY}
```

### Step 5 — Acknowledge & Begin
Post a `START` note letting the system know you are beginning your localized work.
```json
POST {COMMAND_CENTER_URL}/api/activity
{
  "type": "START",
  "message": "[DATE: YYYY-MM-DD] Claimed task {task_title}. Read history. Changing directory to {local_path} and starting work.",
  "repo_name": "{repo_name}",
  "task_id": "{task_id}"
}
```

**✅ Warm-up complete. You may now begin coding.**

---

## 4. Writing Notes — Rules for All Agents

Notes are permanent records in the activity feed. Future agents will read them. Follow these rules:

1. **Date Rule**: Every NOTE must start with `[DATE: YYYY-MM-DD]`. Code evolves. A note from 3 months ago may refer to an outdated pattern. Always check the date.
2. **Quality**: Explain *why* a decision was made (not just what), any constraints, and known tradeoffs.

```json
{
  "type": "NOTE",
  "message": "[DATE: 2026-03-26] Auth module uses JWT RS256. Do not wipe the LEGACY_JWT_SECRET from .env, mobile clients still depend on it.",
  "repo_name": "aiworkfor-me"
}
```

---

## 5. End-of-Session Protocol

When you are finished working on a task, or the human ends your session, execute this tear-down sequence:

```
1. PATCH /api/tasks/{id}/status  → { "status": "DONE" }   (if task completed)
2. POST  /api/activity           → type: WORK_REPORT, message: "[DATE: ...] full summary of everything you did"
3. POST  /api/agents/heartbeat   → { "status": "IDLE" }
```

---

## 6. Submission Schemas (Reference)

```
# Heartbeat
POST /api/agents/heartbeat          { "status": "WORKING" | "IDLE" | "PAUSED" }

# Create Task
POST /api/tasks                     { "repo_name": "...", "title": "...", "description": "...", "priority": "NORMAL" }

# Claim Task
POST /api/tasks/{task_id}/claim     (Empty body, reserves task for you)

# Update Task Status
PATCH /api/tasks/{task_id}/status   { "status": "IN_PROGRESS" | "REVIEW" | "DONE" | "BLOCKED" }

# Activity Log
POST /api/activity
{
  "type": "PROGRESS" | "NOTE" | "COMPLETE" | "BLOCKER" | "WORK_REPORT" | "ERROR" | "BUG_REPORT",
  "message": "[DATE: YYYY-MM-DD] Message body here",
  "repo_name": "repo-name",
  "task_id": "uuid" (optional)
}
```
