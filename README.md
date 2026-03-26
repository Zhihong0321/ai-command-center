# AI Command Center

Central coordination hub for all AI coding agents working across GitHub repos.
Hosted on Railway with PostgreSQL.

## Structure

```
ai-command-center/
├── backend/          # FastAPI + SQLAlchemy + Alembic
├── frontend/         # Next.js 15 (App Router) + Tailwind
└── SKILL.md          # Agent protocol — read this first
```

## Quick Start (Local Dev)

### Backend
```bash
cd backend
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # fill in values
uvicorn main:app --reload
```
API docs: http://localhost:8000/docs

### Frontend
```bash
cd frontend
cp .env.local.example .env.local   # set API URL + admin key
npm install
npm run dev
```
Dashboard: http://localhost:3000

## First-Time Setup

After the backend is running, register your repos and agents:

```bash
# Register a repo
curl -X POST http://localhost:8000/api/repos \
  -H "X-API-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-repo", "display_name": "My Repo", "github_url": "https://github.com/you/my-repo", "category": "api"}'

# Register an agent (returns its unique API key)
curl -X POST http://localhost:8000/api/agents \
  -H "X-API-Key: YOUR_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "gemini", "type": "GEMINI"}'
```

## Deployment on Railway

Deploy as two separate services in the same Railway project:
1. **Backend** — root: `./backend`, env vars: `DATABASE_URL`, `GITHUB_TOKEN`, `ADMIN_API_KEY`, `CORS_ORIGINS`
2. **Frontend** — root: `./frontend`, env vars: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_ADMIN_KEY`
3. **PostgreSQL** — add via Railway plugin, copy `DATABASE_URL` to Backend service

## Agent Protocol

See [SKILL.md](./SKILL.md) — give this file to every AI agent in their context.

## Environment Variables

### Backend
| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `GITHUB_TOKEN` | GitHub PAT with repo read access |
| `ADMIN_API_KEY` | Secret key for admin operations |
| `CORS_ORIGINS` | Comma-separated allowed origins |

### Frontend
| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend URL |
| `NEXT_PUBLIC_ADMIN_KEY` | Admin key (for dashboard operations) |
