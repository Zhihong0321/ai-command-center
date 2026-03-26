from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from app import models

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def get_current_agent(
    api_key: str = Security(api_key_header),
    db: Session = None,
) -> models.Agent:
    agent = db.query(models.Agent).filter(models.Agent.api_key == api_key).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key. Register your agent first.",
        )
    return agent


def require_admin(api_key: str = Security(api_key_header)):
    """Only the ADMIN_API_KEY can call admin-only endpoints (e.g. register agents/repos)."""
    from app.config import settings
    if api_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin key required.",
        )
