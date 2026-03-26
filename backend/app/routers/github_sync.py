from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app import models
from app.database import get_db
from app.auth import require_admin

router = APIRouter(prefix="/api/github", tags=["GitHub"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


class CommitOut(BaseModel):
    sha: str
    author: str
    message: str
    url: str
    committed_at: Optional[datetime]


class PROut(BaseModel):
    pr_number: int
    title: str
    status: str
    url: str
    author: str
    task_id: Optional[str]
    updated_at: Optional[datetime]


@router.post("/sync/{repo_name}", status_code=200)
def sync_repo(
    repo_name: str,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    """Trigger a GitHub sync for a registered repo."""
    _verify_any_key(api_key, db)
    from app.services.github import sync_github_repo
    repo = db.query(models.Repo).filter(models.Repo.name == repo_name).first()
    if not repo:
        raise HTTPException(404, f"Repo '{repo_name}' not found.")
    if not repo.github_url:
        raise HTTPException(400, "Repo has no GitHub URL configured.")
    result = sync_github_repo(repo.id, db)
    return result


@router.get("/commits/{repo_name}", response_model=List[dict])
def get_commits(
    repo_name: str,
    limit: int = 20,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    _verify_any_key(api_key, db)
    repo = db.query(models.Repo).filter(models.Repo.name == repo_name).first()
    if not repo:
        raise HTTPException(404)
    commits = (
        db.query(models.GithubCommit)
        .filter(models.GithubCommit.repo_id == repo.id)
        .order_by(models.GithubCommit.committed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "sha": c.sha,
            "author": c.author,
            "message": c.message,
            "url": c.url,
            "committed_at": c.committed_at.isoformat() if c.committed_at else None,
        }
        for c in commits
    ]


@router.get("/prs/{repo_name}", response_model=List[dict])
def get_prs(
    repo_name: str,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    _verify_any_key(api_key, db)
    repo = db.query(models.Repo).filter(models.Repo.name == repo_name).first()
    if not repo:
        raise HTTPException(404)
    prs = (
        db.query(models.GithubPR)
        .filter(models.GithubPR.repo_id == repo.id)
        .order_by(models.GithubPR.updated_at.desc())
        .all()
    )
    return [
        {
            "pr_number": p.pr_number,
            "title": p.title,
            "status": p.status,
            "url": p.url,
            "author": p.author,
            "task_id": p.task_id,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        for p in prs
    ]


def _verify_any_key(api_key: str, db: Session):
    from app.config import settings
    if api_key == settings.ADMIN_API_KEY:
        return
    agent = db.query(models.Agent).filter(models.Agent.api_key == api_key).first()
    if not agent:
        raise HTTPException(401, "Invalid API key")
