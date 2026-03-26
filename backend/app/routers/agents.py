from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
import secrets

from app import models
from app.database import get_db
from app.auth import require_admin, get_current_agent

router = APIRouter(prefix="/api/agents", tags=["Agents"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str
    type: models.AgentType
    machine_name: Optional[str] = None   # e.g. "home-mac", "work-pc"
    machine_id: Optional[str] = None     # UUID generated once per device

class AgentOut(BaseModel):
    id: str
    name: str
    type: str
    status: str
    machine_name: Optional[str]
    machine_id: Optional[str]
    current_task_id: Optional[str]
    last_seen: Optional[datetime]
    created_at: datetime
    class Config:
        from_attributes = True

class AgentCreateOut(AgentOut):
    api_key: str  # Only returned on creation

class HeartbeatIn(BaseModel):
    status: models.AgentStatus
    machine_name: Optional[str] = None   # agent can update machine_name on heartbeat


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("", response_model=AgentCreateOut, status_code=201)
def register_agent(
    body: AgentCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Admin-only: register a new AI agent and get back its unique API key."""
    existing = db.query(models.Agent).filter(models.Agent.name == body.name).first()
    if existing:
        raise HTTPException(409, detail=f"Agent '{body.name}' already exists.")
    api_key = secrets.token_urlsafe(32)
    agent = models.Agent(
        name=body.name,
        type=body.type,
        api_key=api_key,
        machine_name=body.machine_name,
        machine_id=body.machine_id,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return {**agent.__dict__, "api_key": api_key}


@router.get("", response_model=List[AgentOut])
def list_agents(db: Session = Depends(get_db), api_key: str = Security(api_key_header)):
    """List all registered agents and their current status."""
    _verify_any_key(api_key, db)
    return db.query(models.Agent).all()


@router.get("/me", response_model=AgentOut)
def get_me(
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    """Get the profile of the calling agent."""
    agent = db.query(models.Agent).filter(models.Agent.api_key == api_key).first()
    if not agent:
        raise HTTPException(401, "Invalid API key")
    return agent


@router.post("/heartbeat", response_model=AgentOut)
def heartbeat(
    body: HeartbeatIn,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    """Agent calls this on startup and periodically to report its status."""
    agent = db.query(models.Agent).filter(models.Agent.api_key == api_key).first()
    if not agent:
        raise HTTPException(401, "Invalid API key")
    agent.status = body.status
    agent.last_seen = datetime.utcnow()
    if body.machine_name:
        agent.machine_name = body.machine_name
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=204)
def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent not found")
    db.delete(agent)
    db.commit()


# ─── Helper ───────────────────────────────────────────────────────────────────

def _verify_any_key(api_key: str, db: Session):
    """Accept admin key or any registered agent key."""
    from app.config import settings
    if api_key == settings.ADMIN_API_KEY:
        return
    agent = db.query(models.Agent).filter(models.Agent.api_key == api_key).first()
    if not agent:
        raise HTTPException(401, "Invalid API key")
