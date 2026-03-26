from fastapi import APIRouter, Depends, HTTPException, Security, Query
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel

from app import models
from app.database import get_db

router = APIRouter(prefix="/api/activity", tags=["Activity"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ActivityCreate(BaseModel):
    type: models.ActivityType
    message: str
    repo_name: Optional[str] = None
    task_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ActivityOut(BaseModel):
    id: str
    type: str
    message: str
    metadata_: Optional[Dict[str, Any]]
    created_at: datetime
    agent: Optional[dict]
    repo: Optional[dict]
    task_id: Optional[str]
    class Config:
        from_attributes = True


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def post_activity(
    body: ActivityCreate,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    """Any agent posts an activity update."""
    agent = _get_agent(api_key, db)

    repo_id = None
    if body.repo_name:
        repo = db.query(models.Repo).filter(models.Repo.name == body.repo_name).first()
        if repo:
            repo_id = repo.id

    log = models.ActivityLog(
        agent_id=agent.id,
        repo_id=repo_id,
        task_id=body.task_id,
        type=body.type,
        message=body.message,
        metadata_=body.metadata,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    # Stamp repo freshness
    if repo_id:
        repo_obj = db.query(models.Repo).filter(models.Repo.id == repo_id).first()
        if repo_obj:
            repo_obj.last_activity_at = datetime.utcnow()
            db.commit()
    return {"id": log.id, "created_at": log.created_at}


@router.get("", response_model=List[dict])
def get_activity(
    repo: Optional[str] = Query(None),
    agent: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    """Fetch the activity feed, filterable by repo, agent, and type."""
    _verify_any_key(api_key, db)
    q = db.query(models.ActivityLog).options(
        joinedload(models.ActivityLog.agent),
        joinedload(models.ActivityLog.repo),
    )
    if repo:
        r = db.query(models.Repo).filter(models.Repo.name == repo).first()
        if r:
            q = q.filter(models.ActivityLog.repo_id == r.id)
    if agent:
        a = db.query(models.Agent).filter(models.Agent.name == agent).first()
        if a:
            q = q.filter(models.ActivityLog.agent_id == a.id)
    if type:
        q = q.filter(models.ActivityLog.type == type.upper())

    logs = q.order_by(models.ActivityLog.created_at.desc()).limit(limit).all()

    return [
        {
            "id": l.id,
            "type": l.type.value,
            "message": l.message,
            "metadata": l.metadata_,
            "created_at": l.created_at.isoformat(),
            "agent": {"id": l.agent.id, "name": l.agent.name, "type": l.agent.type.value} if l.agent else None,
            "repo": {"id": l.repo.id, "name": l.repo.name} if l.repo else None,
            "task_id": l.task_id,
        }
        for l in logs
    ]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_agent(api_key: str, db: Session) -> models.Agent:
    agent = db.query(models.Agent).filter(models.Agent.api_key == api_key).first()
    if not agent:
        from app.config import settings
        if api_key == settings.ADMIN_API_KEY:
            a = db.query(models.Agent).filter(models.Agent.name == "system").first()
            if a:
                return a
        raise HTTPException(401, "Invalid API key.")
    return agent


def _verify_any_key(api_key: str, db: Session):
    from app.config import settings
    if api_key == settings.ADMIN_API_KEY:
        return
    agent = db.query(models.Agent).filter(models.Agent.api_key == api_key).first()
    if not agent:
        raise HTTPException(401, "Invalid API key")
