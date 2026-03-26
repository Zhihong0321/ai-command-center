from fastapi import APIRouter, Depends, HTTPException, Security, Query
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app import models
from app.database import get_db

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    repo_name: str
    title: str
    description: Optional[str] = None
    priority: Optional[models.TaskPriority] = models.TaskPriority.NORMAL
    github_issue_url: Optional[str] = None

class TaskStatusUpdate(BaseModel):
    status: models.TaskStatus
    github_pr_url: Optional[str] = None

class HandoffIn(BaseModel):
    to_agent_name: str
    note: Optional[str] = None

class AgentSummary(BaseModel):
    id: str
    name: str
    type: str
    class Config:
        from_attributes = True

class RepoSummary(BaseModel):
    id: str
    name: str
    display_name: Optional[str]
    class Config:
        from_attributes = True

class TaskOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    status: str
    priority: str
    repo: RepoSummary
    creator: Optional[AgentSummary]
    assignee: Optional[AgentSummary]
    github_issue_url: Optional[str]
    github_pr_url: Optional[str]
    claimed_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    class Config:
        from_attributes = True


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("", response_model=TaskOut, status_code=201)
def create_task(
    body: TaskCreate,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    agent = _get_agent(api_key, db)
    repo = db.query(models.Repo).filter(models.Repo.name == body.repo_name).first()
    if not repo:
        raise HTTPException(404, f"Repo '{body.repo_name}' not found.")

    task = models.Task(
        repo_id=repo.id,
        title=body.title,
        description=body.description,
        priority=body.priority,
        github_issue_url=body.github_issue_url,
        created_by_id=agent.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _load_task(task.id, db)


@router.get("", response_model=List[TaskOut])
def list_tasks(
    repo: Optional[str] = Query(None, description="Filter by repo name"),
    status: Optional[str] = Query(None, description="Filter by status"),
    assigned_to: Optional[str] = Query(None, description="Filter by agent name"),
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    _verify_any_key(api_key, db)
    q = db.query(models.Task).options(
        joinedload(models.Task.repo),
        joinedload(models.Task.creator),
        joinedload(models.Task.assignee),
    )
    if repo:
        r = db.query(models.Repo).filter(models.Repo.name == repo).first()
        if r:
            q = q.filter(models.Task.repo_id == r.id)
    if status:
        q = q.filter(models.Task.status == status.upper())
    if assigned_to:
        a = db.query(models.Agent).filter(models.Agent.name == assigned_to).first()
        if a:
            q = q.filter(models.Task.assigned_to_id == a.id)
    return q.order_by(models.Task.created_at.desc()).all()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    _verify_any_key(api_key, db)
    return _load_task(task_id, db)


@router.post("/{task_id}/claim", response_model=TaskOut)
def claim_task(
    task_id: str,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    """
    Claim an OPEN task. Returns 409 with current owner if already claimed.
    """
    agent = _get_agent(api_key, db)
    task = db.query(models.Task).filter(models.Task.id == task_id).with_for_update().first()
    if not task:
        raise HTTPException(404, "Task not found.")
    if task.status not in (models.TaskStatus.OPEN,):
        owner_name = task.assignee.name if task.assignee else "unknown"
        raise HTTPException(
            409,
            detail={
                "error": "Task already claimed.",
                "current_owner": owner_name,
                "task_status": task.status.value,
            },
        )
    task.status = models.TaskStatus.CLAIMED
    task.assigned_to_id = agent.id
    task.claimed_at = datetime.utcnow()
    agent.current_task_id = task.id
    db.commit()
    return _load_task(task_id, db)


@router.patch("/{task_id}/status", response_model=TaskOut)
def update_task_status(
    task_id: str,
    body: TaskStatusUpdate,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    agent = _get_agent(api_key, db)
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found.")
    task.status = body.status
    if body.github_pr_url:
        task.github_pr_url = body.github_pr_url
    if body.status == models.TaskStatus.DONE:
        task.completed_at = datetime.utcnow()
        # Free the agent
        if agent.current_task_id == task.id:
            agent.current_task_id = None
    db.commit()
    return _load_task(task_id, db)


@router.post("/{task_id}/handoff", response_model=TaskOut)
def handoff_task(
    task_id: str,
    body: HandoffIn,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    """Formally hand a task off to another agent."""
    current_agent = _get_agent(api_key, db)
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found.")

    new_owner = db.query(models.Agent).filter(models.Agent.name == body.to_agent_name).first()
    if not new_owner:
        raise HTTPException(404, f"Agent '{body.to_agent_name}' not found.")

    task.assigned_to_id = new_owner.id
    task.status = models.TaskStatus.CLAIMED
    task.claimed_at = datetime.utcnow()

    # Log the handoff
    log_msg = f"Task handed off from {current_agent.name} to {new_owner.name}."
    if body.note:
        log_msg += f" Note: {body.note}"

    activity = models.ActivityLog(
        agent_id=current_agent.id,
        repo_id=task.repo_id,
        task_id=task.id,
        type=models.ActivityType.HANDOFF,
        message=log_msg,
    )
    db.add(activity)

    if current_agent.current_task_id == task.id:
        current_agent.current_task_id = None

    db.commit()
    return _load_task(task_id, db)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_agent(api_key: str, db: Session) -> models.Agent:
    from app.config import settings
    if api_key == settings.ADMIN_API_KEY:
        # Find or create a "system" agent
        system = db.query(models.Agent).filter(models.Agent.name == "system").first()
        if system:
            return system
        raise HTTPException(403, "Use an agent API key, not admin key, for this action.")
    agent = db.query(models.Agent).filter(models.Agent.api_key == api_key).first()
    if not agent:
        raise HTTPException(401, "Invalid API key.")
    return agent


def _verify_any_key(api_key: str, db: Session):
    from app.config import settings
    if api_key == settings.ADMIN_API_KEY:
        return
    agent = db.query(models.Agent).filter(models.Agent.api_key == api_key).first()
    if not agent:
        raise HTTPException(401, "Invalid API key")


def _load_task(task_id: str, db: Session) -> models.Task:
    task = db.query(models.Task).options(
        joinedload(models.Task.repo),
        joinedload(models.Task.creator),
        joinedload(models.Task.assignee),
    ).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    return task
