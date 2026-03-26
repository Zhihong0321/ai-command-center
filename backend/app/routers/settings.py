from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app import models
from app.database import get_db
from app.auth import require_admin

router = APIRouter(prefix="/api/settings", tags=["Settings"])

class SettingBase(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class SettingOut(SettingBase):
    class Config:
        from_attributes = True

@router.get("", response_model=List[SettingOut])
def get_settings(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    """Admin only: list all settings."""
    return db.query(models.Setting).all()

@router.get("/{key}", response_model=SettingOut)
def get_setting(
    key: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    """Admin only: get a specific setting."""
    setting = db.query(models.Setting).filter(models.Setting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting

@router.post("", response_model=SettingOut)
def update_setting(
    setting: SettingBase,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin)
):
    """Admin only: create or update a setting."""
    db_setting = db.query(models.Setting).filter(models.Setting.key == setting.key).first()
    if db_setting:
        db_setting.value = setting.value
        db_setting.description = setting.description
    else:
        db_setting = models.Setting(**setting.dict())
        db.add(db_setting)
    db.commit()
    db.refresh(db_setting)
    return db_setting
