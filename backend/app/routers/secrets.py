from fastapi import APIRouter, Depends, HTTPException, Security, Query
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app import models
from app.database import get_db
from app.auth import require_admin
from app.services.encryption import encrypt_secret, decrypt_secret

router = APIRouter(prefix="/api/secrets", tags=["Secrets Vault"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class SecretCreate(BaseModel):
    label: str                                      # e.g. "Production Postgres DB"
    value: str                                      # the actual credential / connection string
    unlock_key: str                                 # chosen by human, never stored
    description: Optional[str] = None
    key_type: Optional[str] = "DATABASE"            # DATABASE | API_KEY | SSH | OTHER
    repo_name: Optional[str] = None                 # associate with a repo (optional)

class SecretReveal(BaseModel):
    unlock_key: str                                 # must be provided by human to agent


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def store_secret(
    body: SecretCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """
    Admin-only: store an encrypted credential.
    The unlock_key is used to encrypt the value but is NEVER saved.
    The response includes the secret's ID — share this ID with agents.
    """
    repo_id = None
    if body.repo_name:
        repo = db.query(models.Repo).filter(models.Repo.name == body.repo_name).first()
        if not repo:
            raise HTTPException(404, f"Repo '{body.repo_name}' not found.")
        repo_id = repo.id

    encrypted_value, salt = encrypt_secret(body.value, body.unlock_key)

    # Find the system/admin agent to record as creator (if exists)
    creator_id = None
    sys_agent = db.query(models.Agent).filter(models.Agent.name == "system").first()
    if sys_agent:
        creator_id = sys_agent.id

    secret = models.SecretKey(
        label=body.label,
        description=body.description,
        key_type=body.key_type,
        repo_id=repo_id,
        created_by_id=creator_id,
        encrypted_value=encrypted_value,
        salt=salt,
    )
    db.add(secret)
    db.commit()
    db.refresh(secret)

    return {
        "id": secret.id,
        "label": secret.label,
        "key_type": secret.key_type,
        "repo_name": body.repo_name,
        "created_at": secret.created_at.isoformat(),
        "message": "Secret stored. The unlock_key was NOT saved. Keep it safe — you will need to give it to agents manually.",
    }


@router.get("", response_model=List[dict])
def list_secrets(
    repo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    """
    List all secrets (labels only — values are NEVER returned here).
    Any registered agent or admin can see what secrets exist.
    """
    _verify_any_key(api_key, db)
    q = db.query(models.SecretKey)
    if repo:
        r = db.query(models.Repo).filter(models.Repo.name == repo).first()
        if r:
            q = q.filter(models.SecretKey.repo_id == r.id)
    secrets = q.order_by(models.SecretKey.created_at.desc()).all()

    result = []
    for s in secrets:
        repo_obj = db.query(models.Repo).filter(models.Repo.id == s.repo_id).first() if s.repo_id else None
        last_by = db.query(models.Agent).filter(models.Agent.id == s.last_accessed_by_id).first() if s.last_accessed_by_id else None
        result.append({
            "id": s.id,
            "label": s.label,
            "description": s.description,
            "key_type": s.key_type,
            "repo": {"name": repo_obj.name, "display_name": repo_obj.display_name} if repo_obj else None,
            "created_at": s.created_at.isoformat(),
            "last_accessed_at": s.last_accessed_at.isoformat() if s.last_accessed_at else None,
            "last_accessed_by": last_by.name if last_by else None,
        })
    return result


@router.post("/{secret_id}/reveal")
def reveal_secret(
    secret_id: str,
    body: SecretReveal,
    db: Session = Depends(get_db),
    api_key: str = Security(api_key_header),
):
    """
    Reveal (decrypt) a secret.

    The agent must:
    1. Know the secret's ID (visible in GET /api/secrets)
    2. Supply the unlock_key — obtained directly from the human operator

    If the unlock_key is wrong, a 403 is returned. The attempt is logged.
    """
    agent = _get_agent_or_admin(api_key, db)
    secret = db.query(models.SecretKey).filter(models.SecretKey.id == secret_id).first()
    if not secret:
        raise HTTPException(404, "Secret not found.")

    try:
        plaintext = decrypt_secret(secret.encrypted_value, secret.salt, body.unlock_key)
    except ValueError:
        # Log the failed attempt to activity feed
        _log_access_failed(agent, secret, db)
        raise HTTPException(
            403,
            detail="Invalid unlock key. The secret could not be decrypted. Ask the human operator for the correct unlock key."
        )

    # Audit: record who accessed it and when
    secret.last_accessed_at = datetime.utcnow()
    secret.last_accessed_by_id = agent.id if agent else None
    db.commit()

    # Log successful access to activity feed
    _log_access_success(agent, secret, db)

    return {
        "id": secret.id,
        "label": secret.label,
        "key_type": secret.key_type,
        "value": plaintext,
        "accessed_at": secret.last_accessed_at.isoformat(),
        "warning": "Do not store this credential in any file or log. Use it directly in your session only.",
    }


@router.delete("/{secret_id}", status_code=204)
def delete_secret(
    secret_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    secret = db.query(models.SecretKey).filter(models.SecretKey.id == secret_id).first()
    if not secret:
        raise HTTPException(404)
    db.delete(secret)
    db.commit()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_agent_or_admin(api_key: str, db: Session) -> Optional[models.Agent]:
    from app.config import settings
    if api_key == settings.ADMIN_API_KEY:
        return db.query(models.Agent).filter(models.Agent.name == "system").first()
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


def _log_access_success(agent: Optional[models.Agent], secret: models.SecretKey, db: Session):
    if not agent:
        return
    log = models.ActivityLog(
        agent_id=agent.id,
        repo_id=secret.repo_id,
        type=models.ActivityType.NOTE,
        message=f"[VAULT ACCESS] Agent '{agent.name}' successfully revealed secret: '{secret.label}'",
        metadata_={"secret_id": secret.id, "secret_label": secret.label, "success": True},
    )
    db.add(log)
    db.commit()


def _log_access_failed(agent: Optional[models.Agent], secret: models.SecretKey, db: Session):
    if not agent:
        return
    log = models.ActivityLog(
        agent_id=agent.id,
        repo_id=secret.repo_id,
        type=models.ActivityType.ERROR,
        message=f"[VAULT FAILED] Agent '{agent.name}' attempted secret '{secret.label}' with wrong unlock key.",
        metadata_={"secret_id": secret.id, "secret_label": secret.label, "success": False},
    )
    db.add(log)
    db.commit()
