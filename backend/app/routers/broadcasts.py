from fastapi import APIRouter, Depends, HTTPException, Security, Query
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app import models
from app.database import get_db
from app.auth import require_admin

router = APIRouter(prefix="/api/broadcasts", tags=["Broadcasts"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class BroadcastCreate(BaseModel):
    message: str
    scope: str = "ALL"  # ALL | REPO:repo_name | AGENT:agent_name
    expires_at: Optional[datetime] = None

class BroadcastOut(BaseModel):
    id: str
    message: str
    scope: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]
    creator: Optional[dict]
    class Config:
        from_attributes = True


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def create_broadcast(
    body: BroadcastCreate,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    """Human (admin) posts a broadcast message to all or specific agents/repos."""
    from app.config import settings
    agent_id = None
    if api_key != settings.ADMIN_API_KEY:
        agent = db.query(models.Agent).filter(models.Agent.api_key == api_key).first()
        if not agent:
            raise HTTPException(401, "Invalid API key")
        if agent.type != models.AgentType.HUMAN:
            raise HTTPException(403, "Only HUMAN agents or admin can broadcast.")
        agent_id = agent.id
    else:
        # Find system agent or leave null
        sys_agent = db.query(models.Agent).filter(models.Agent.name == "system").first()
        if sys_agent:
            agent_id = sys_agent.id

    bc = models.Broadcast(
        created_by_id=agent_id,
        message=body.message,
        scope=body.scope,
        expires_at=body.expires_at,
    )
    db.add(bc)
    db.commit()
    db.refresh(bc)
    return {"id": bc.id, "message": bc.message, "scope": bc.scope, "created_at": bc.created_at}


@router.get("", response_model=List[dict])
def get_broadcasts(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    """Agents read this at session start to get current human instructions."""
    _verify_any_key(api_key, db)
    q = db.query(models.Broadcast)
    if active_only:
        now = datetime.utcnow()
        q = q.filter(
            models.Broadcast.is_active == True,
            (models.Broadcast.expires_at == None) | (models.Broadcast.expires_at > now),
        )
    bcs = q.order_by(models.Broadcast.created_at.desc()).all()
    return [
        {
            "id": b.id,
            "message": b.message,
            "scope": b.scope,
            "is_active": b.is_active,
            "created_at": b.created_at.isoformat(),
            "expires_at": b.expires_at.isoformat() if b.expires_at else None,
        }
        for b in bcs
    ]


@router.patch("/{broadcast_id}/deactivate", status_code=200)
def deactivate_broadcast(
    broadcast_id: str,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    from app.config import settings
    if api_key != settings.ADMIN_API_KEY:
        agent = db.query(models.Agent).filter(models.Agent.api_key == api_key).first()
        if not agent or agent.type != models.AgentType.HUMAN:
            raise HTTPException(403, "Only admin or HUMAN agents can deactivate broadcasts.")
    bc = db.query(models.Broadcast).filter(models.Broadcast.id == broadcast_id).first()
    if not bc:
        raise HTTPException(404, "Broadcast not found.")
    bc.is_active = False
    db.commit()
    return {"ok": True}


# ─── Helper ───────────────────────────────────────────────────────────────────

def _verify_any_key(api_key: str, db: Session):
    from app.config import settings
    if api_key == settings.ADMIN_API_KEY:
        return
    agent = db.query(models.Agent).filter(models.Agent.api_key == api_key).first()
    if not agent:
        raise HTTPException(401, "Invalid API key")
