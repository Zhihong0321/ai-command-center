import os
from fastapi import FastAPI, Depends, Security
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.config import settings
from app.database import get_db, engine
from app import models
from app.routers import agents, repos, tasks, activity, broadcasts, github_sync, bug_reports, secrets, settings

# Create all tables on startup (Alembic handles migrations in prod)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Command Center",
    description="Central coordination hub for AI coding agents across GitHub repos.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(agents.router)
app.include_router(repos.router)
app.include_router(tasks.router)
app.include_router(activity.router)
app.include_router(broadcasts.router)
app.include_router(github_sync.router)
app.include_router(bug_reports.router)
app.include_router(secrets.router)
app.include_router(settings.router)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AI Command Center", "time": datetime.utcnow().isoformat()}


@app.get("/api/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    """
    One-call summary for the Command Hub dashboard:
    - Active agents
    - Recent activity (last 20)
    - Task stats per repo
    - Active broadcasts
    """
    _verify_any_key(api_key, db)
    now = datetime.utcnow()

    # Active agents (seen in last 15 min)
    cutoff = now - timedelta(minutes=15)
    active_agents = (
        db.query(models.Agent)
        .filter(models.Agent.last_seen >= cutoff)
        .all()
    )

    # Recent activity
    recent = (
        db.query(models.ActivityLog)
        .order_by(models.ActivityLog.created_at.desc())
        .limit(20)
        .all()
    )

    # Repo task stats
    repos = db.query(models.Repo).all()
    repo_stats = []
    for r in repos:
        open_count = db.query(models.Task).filter(
            models.Task.repo_id == r.id,
            models.Task.status == models.TaskStatus.OPEN
        ).count()
        in_progress = db.query(models.Task).filter(
            models.Task.repo_id == r.id,
            models.Task.status.in_([models.TaskStatus.CLAIMED, models.TaskStatus.IN_PROGRESS])
        ).count()
        done = db.query(models.Task).filter(
            models.Task.repo_id == r.id,
            models.Task.status == models.TaskStatus.DONE
        ).count()
        repo_stats.append({
            "id": r.id,
            "name": r.name,
            "display_name": r.display_name,
            "github_url": r.github_url,
            "railway_url": r.railway_url,
            "tasks": {"open": open_count, "in_progress": in_progress, "done": done},
            "last_synced_at": r.last_synced_at.isoformat() if r.last_synced_at else None,
            "last_commit_date": r.last_commit_date.isoformat() if r.last_commit_date else None,
            "last_activity_at": r.last_activity_at.isoformat() if r.last_activity_at else None,
        })

    # Active broadcasts
    broadcasts_q = db.query(models.Broadcast).filter(
        models.Broadcast.is_active == True,
        (models.Broadcast.expires_at == None) | (models.Broadcast.expires_at > now),
    ).all()

    return {
        "active_agents": [
            {"id": a.id, "name": a.name, "type": a.type.value, "status": a.status.value, "last_seen": a.last_seen.isoformat()}
            for a in active_agents
        ],
        "recent_activity": [
            {
                "id": l.id,
                "type": l.type.value,
                "message": l.message,
                "created_at": l.created_at.isoformat(),
                "agent_name": l.agent.name if l.agent else None,
                "repo_name": l.repo.name if l.repo else None,
            }
            for l in recent
        ],
        "repos": repo_stats,
        "active_broadcasts": [
            {"id": b.id, "message": b.message, "scope": b.scope, "created_at": b.created_at.isoformat()}
            for b in broadcasts_q
        ],
        "generated_at": now.isoformat(),
    }


def _verify_any_key(api_key: str, db: Session):
    if api_key == settings.ADMIN_API_KEY:
        return
    agent = db.query(models.Agent).filter(models.Agent.api_key == api_key).first()
    if not agent:
        from fastapi import HTTPException
        raise HTTPException(401, "Invalid API key")

# --- Serve Frontend SPA (Must be at the bottom) ---
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'out')

if os.path.isdir(FRONTEND_DIR):
    # Mount specific Next.js asset directories to bypass the catch-all
    if os.path.isdir(os.path.join(FRONTEND_DIR, "_next")):
        app.mount("/_next", StaticFiles(directory=os.path.join(FRONTEND_DIR, "_next")), name="next_assets")
        
    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        # Ignore /api routes (though they should have been caught by routers above)
        if full_path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="API route not found")
            
        path = os.path.join(FRONTEND_DIR, full_path)
        # If the file exists directly (like favicon.ico, images), serve it
        if os.path.isfile(path):
            return FileResponse(path)
        
        # Fallback to index.html for SPA hydration
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Frontend build not found")
