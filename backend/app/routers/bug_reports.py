from fastapi import APIRouter, Depends, HTTPException, Security, Query
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app import models
from app.database import get_db

router = APIRouter(prefix="/api/bugs", tags=["Bug Reports"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class BugReportCreate(BaseModel):
    repo_name: str
    title: str
    severity: Optional[models.BugSeverity] = models.BugSeverity.MEDIUM
    area: Optional[str] = None                      # e.g. "Admin Panel > Finance"
    site_url: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    observed_behavior: Optional[str] = None
    expected_behavior: Optional[str] = None
    analysis: Optional[str] = None                  # Agent's diagnosis
    screenshot_url: Optional[str] = None
    task_id: Optional[str] = None


class BugStatusUpdate(BaseModel):
    status: models.BugStatus


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def file_bug_report(
    body: BugReportCreate,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    """
    Any agent can file a structured bug report.
    Especially useful for browser-testing agents (e.g. Openclaw) that
    navigate a live site, discover an issue, diagnose it, and file
    a detailed, analyzed bug report for the human or dev team.
    """
    agent = _get_agent(api_key, db)
    repo = db.query(models.Repo).filter(models.Repo.name == body.repo_name).first()
    if not repo:
        raise HTTPException(404, f"Repo '{body.repo_name}' not found.")

    bug = models.BugReport(
        repo_id=repo.id,
        filed_by_id=agent.id,
        task_id=body.task_id,
        severity=body.severity,
        title=body.title,
        site_url=body.site_url,
        area=body.area,
        steps_to_reproduce=body.steps_to_reproduce,
        observed_behavior=body.observed_behavior,
        expected_behavior=body.expected_behavior,
        analysis=body.analysis,
        screenshot_url=body.screenshot_url,
    )
    db.add(bug)

    # Also write an activity log entry so it shows in the feed
    log = models.ActivityLog(
        agent_id=agent.id,
        repo_id=repo.id,
        task_id=body.task_id,
        type=models.ActivityType.BUG_REPORT,
        message=f"[BUG {body.severity.value}] {body.title}" + (f" — Area: {body.area}" if body.area else ""),
        metadata_={"bug_id": None, "site_url": body.site_url},  # bug_id filled after commit
    )
    db.add(log)
    db.commit()
    db.refresh(bug)
    # Update activity log with bug id
    log.metadata_ = {"bug_id": bug.id, "site_url": body.site_url}
    db.commit()

    return {
        "id": bug.id,
        "title": bug.title,
        "severity": bug.severity.value,
        "status": bug.status.value,
        "repo": body.repo_name,
        "filed_by": agent.name,
        "created_at": bug.created_at.isoformat(),
    }


@router.get("", response_model=List[dict])
def list_bugs(
    repo: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    _verify_any_key(api_key, db)
    q = db.query(models.BugReport)
    if repo:
        r = db.query(models.Repo).filter(models.Repo.name == repo).first()
        if r:
            q = q.filter(models.BugReport.repo_id == r.id)
    if status:
        q = q.filter(models.BugReport.status == status.upper())
    if severity:
        q = q.filter(models.BugReport.severity == severity.upper())
    bugs = q.order_by(models.BugReport.created_at.desc()).limit(limit).all()
    return [_serialize_bug(b, db) for b in bugs]


@router.get("/{bug_id}")
def get_bug(
    bug_id: str,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    _verify_any_key(api_key, db)
    bug = db.query(models.BugReport).filter(models.BugReport.id == bug_id).first()
    if not bug:
        raise HTTPException(404, "Bug report not found")
    return _serialize_bug(bug, db)


@router.patch("/{bug_id}/status")
def update_bug_status(
    bug_id: str,
    body: BugStatusUpdate,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    _verify_any_key(api_key, db)
    bug = db.query(models.BugReport).filter(models.BugReport.id == bug_id).first()
    if not bug:
        raise HTTPException(404)
    bug.status = body.status
    db.commit()
    return {"ok": True, "status": bug.status.value}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _serialize_bug(bug: models.BugReport, db: Session) -> dict:
    repo = db.query(models.Repo).filter(models.Repo.id == bug.repo_id).first()
    agent = db.query(models.Agent).filter(models.Agent.id == bug.filed_by_id).first()
    return {
        "id": bug.id,
        "title": bug.title,
        "severity": bug.severity.value,
        "status": bug.status.value,
        "area": bug.area,
        "site_url": bug.site_url,
        "steps_to_reproduce": bug.steps_to_reproduce,
        "observed_behavior": bug.observed_behavior,
        "expected_behavior": bug.expected_behavior,
        "analysis": bug.analysis,
        "screenshot_url": bug.screenshot_url,
        "repo": {"id": repo.id, "name": repo.name} if repo else None,
        "filed_by": {"id": agent.id, "name": agent.name, "type": agent.type.value} if agent else None,
        "task_id": bug.task_id,
        "created_at": bug.created_at.isoformat(),
        "updated_at": bug.updated_at.isoformat() if bug.updated_at else None,
    }


def _get_agent(api_key: str, db: Session) -> models.Agent:
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
