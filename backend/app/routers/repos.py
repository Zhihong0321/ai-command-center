from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app import models
from app.database import get_db
from app.auth import require_admin

router = APIRouter(prefix="/api/repos", tags=["Repos"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class RepoCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    github_url: Optional[str] = None
    railway_url: Optional[str] = None
    category: Optional[str] = "general"
    description: Optional[str] = None
    local_path: Optional[str] = None

class RepoUpdate(BaseModel):
    display_name: Optional[str] = None
    github_url: Optional[str] = None
    railway_url: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    local_path: Optional[str] = None

class RepoOut(BaseModel):
    id: str
    name: str
    display_name: Optional[str]
    github_url: Optional[str]
    railway_url: Optional[str]
    category: Optional[str]
    description: Optional[str]
    local_path: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("", response_model=RepoOut, status_code=201)
def register_repo(
    body: RepoCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    existing = db.query(models.Repo).filter(models.Repo.name == body.name).first()
    if existing:
        raise HTTPException(409, f"Repo '{body.name}' already registered.")
    repo = models.Repo(**body.model_dump())
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


@router.get("", response_model=List[RepoOut])
def list_repos(
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    _verify_any_key(api_key, db)
    return db.query(models.Repo).all()


@router.get("/{repo_name}", response_model=RepoOut)
def get_repo(
    repo_name: str,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    _verify_any_key(api_key, db)
    repo = db.query(models.Repo).filter(models.Repo.name == repo_name).first()
    if not repo:
        raise HTTPException(404, f"Repo '{repo_name}' not found.")
    return repo


@router.patch("/{repo_name}", response_model=RepoOut)
def update_repo(
    repo_name: str,
    body: RepoUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    repo = db.query(models.Repo).filter(models.Repo.name == repo_name).first()
    if not repo:
        raise HTTPException(404, f"Repo '{repo_name}' not found.")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(repo, k, v)
    db.commit()
    db.refresh(repo)
    return repo


@router.delete("/{repo_name}", status_code=204)
def delete_repo(
    repo_name: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    repo = db.query(models.Repo).filter(models.Repo.name == repo_name).first()
    if not repo:
        raise HTTPException(404)
    db.delete(repo)
    db.commit()


# ─── Helper ───────────────────────────────────────────────────────────────────

def _verify_any_key(api_key: str, db: Session):
    from app.config import settings
    if api_key == settings.ADMIN_API_KEY:
        return
    agent = db.query(models.Agent).filter(models.Agent.api_key == api_key).first()
    if not agent:
        raise HTTPException(401, "Invalid API key")
