import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, ForeignKey, Integer, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


# ─── Enums ────────────────────────────────────────────────────────────────────

class AgentType(str, enum.Enum):
    CODEX = "CODEX"
    GEMINI = "GEMINI"
    MINIMAX = "MINIMAX"
    CLAUDE = "CLAUDE"
    CURSOR = "CURSOR"
    HUMAN = "HUMAN"
    OTHER = "OTHER"


class AgentStatus(str, enum.Enum):
    IDLE = "IDLE"
    WORKING = "WORKING"
    PAUSED = "PAUSED"
    OFFLINE = "OFFLINE"


class TaskStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLAIMED = "CLAIMED"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW = "REVIEW"
    DONE = "DONE"
    BLOCKED = "BLOCKED"


class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActivityType(str, enum.Enum):
    START = "START"
    PROGRESS = "PROGRESS"
    BLOCKER = "BLOCKER"
    COMPLETE = "COMPLETE"
    NOTE = "NOTE"
    ERROR = "ERROR"
    HANDOFF = "HANDOFF"
    # Extended types
    BUG_REPORT = "BUG_REPORT"
    QUESTION = "QUESTION"
    ANALYSIS = "ANALYSIS"
    WORK_REPORT = "WORK_REPORT"
    TEST_RESULT = "TEST_RESULT"


# ─── Models ───────────────────────────────────────────────────────────────────

class Repo(Base):
    __tablename__ = "repos"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200))
    github_url = Column(Text)
    railway_url = Column(Text)
    category = Column(String(50), default="general")
    description = Column(Text)
    local_path = Column(Text, nullable=True)           # absolute local folder path, e.g. G:\\my-project
    last_synced_at = Column(DateTime, nullable=True)   # last GitHub sync
    last_commit_date = Column(DateTime, nullable=True) # date of latest commit pulled
    last_activity_at = Column(DateTime, nullable=True) # last agent activity
    created_at = Column(DateTime, default=datetime.utcnow)

    tasks = relationship("Task", back_populates="repo")
    activity_logs = relationship("ActivityLog", back_populates="repo")
    commits = relationship("GithubCommit", back_populates="repo")
    prs = relationship("GithubPR", back_populates="repo")


class Agent(Base):
    __tablename__ = "agents"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(100), unique=True, nullable=False, index=True)
    type = Column(SAEnum(AgentType), nullable=False, default=AgentType.OTHER)
    api_key = Column(String(200), unique=True, nullable=False, index=True)
    status = Column(SAEnum(AgentStatus), default=AgentStatus.OFFLINE)
    # Machine identification (human-readable, e.g. "home-mac", "work-pc")
    machine_name = Column(String(100), nullable=True)
    machine_id = Column(String(200), nullable=True)  # UUID generated once per device
    current_task_id = Column(UUID(as_uuid=False), nullable=True)
    last_seen = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    tasks_created = relationship("Task", foreign_keys="Task.created_by_id", back_populates="creator")
    tasks_assigned = relationship("Task", foreign_keys="Task.assigned_to_id", back_populates="assignee")
    activity_logs = relationship("ActivityLog", back_populates="agent")
    broadcasts = relationship("Broadcast", back_populates="creator")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    repo_id = Column(UUID(as_uuid=False), ForeignKey("repos.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.OPEN, index=True)
    priority = Column(SAEnum(TaskPriority), default=TaskPriority.NORMAL)
    created_by_id = Column(UUID(as_uuid=False), ForeignKey("agents.id"))
    assigned_to_id = Column(UUID(as_uuid=False), ForeignKey("agents.id"), nullable=True)
    github_issue_url = Column(Text)
    github_pr_url = Column(Text)
    claimed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    repo = relationship("Repo", back_populates="tasks")
    creator = relationship("Agent", foreign_keys=[created_by_id], back_populates="tasks_created")
    assignee = relationship("Agent", foreign_keys=[assigned_to_id], back_populates="tasks_assigned")
    activity_logs = relationship("ActivityLog", back_populates="task")


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    agent_id = Column(UUID(as_uuid=False), ForeignKey("agents.id"), nullable=False)
    repo_id = Column(UUID(as_uuid=False), ForeignKey("repos.id"), nullable=True)
    task_id = Column(UUID(as_uuid=False), ForeignKey("tasks.id"), nullable=True)
    type = Column(SAEnum(ActivityType), nullable=False)
    message = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    agent = relationship("Agent", back_populates="activity_logs")
    repo = relationship("Repo", back_populates="activity_logs")
    task = relationship("Task", back_populates="activity_logs")


class Broadcast(Base):
    __tablename__ = "broadcasts"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    created_by_id = Column(UUID(as_uuid=False), ForeignKey("agents.id"))
    message = Column(Text, nullable=False)
    scope = Column(String(100), default="ALL")  # ALL | REPO:id | AGENT:id
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    creator = relationship("Agent", back_populates="broadcasts")


class GithubCommit(Base):
    __tablename__ = "github_commits"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    repo_id = Column(UUID(as_uuid=False), ForeignKey("repos.id"), nullable=False)
    sha = Column(String(40), index=True)
    author = Column(String(200))
    message = Column(Text)
    url = Column(Text)
    committed_at = Column(DateTime)
    synced_at = Column(DateTime, default=datetime.utcnow)

    repo = relationship("Repo", back_populates="commits")


class GithubPR(Base):
    __tablename__ = "github_prs"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    repo_id = Column(UUID(as_uuid=False), ForeignKey("repos.id"), nullable=False)
    pr_number = Column(Integer)
    title = Column(String(500))
    status = Column(String(20), default="open")  # open | closed | merged
    url = Column(Text)
    author = Column(String(200))
    task_id = Column(UUID(as_uuid=False), nullable=True)
    updated_at = Column(DateTime)
    synced_at = Column(DateTime, default=datetime.utcnow)

    repo = relationship("Repo", back_populates="prs")


class BugSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class BugStatus(str, enum.Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    CONFIRMED = "CONFIRMED"
    FIXED = "FIXED"
    WONT_FIX = "WONT_FIX"


class BugReport(Base):
    """
    Structured bug report filed by any agent (especially browser-testing agents like Openclaw).
    Unlike a generic activity log, a BugReport has structured fields for proper triage.
    """
    __tablename__ = "bug_reports"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    repo_id = Column(UUID(as_uuid=False), ForeignKey("repos.id"), nullable=False)
    filed_by_id = Column(UUID(as_uuid=False), ForeignKey("agents.id"), nullable=False)
    task_id = Column(UUID(as_uuid=False), ForeignKey("tasks.id"), nullable=True)
    severity = Column(SAEnum(BugSeverity), default=BugSeverity.MEDIUM)
    status = Column(SAEnum(BugStatus), default=BugStatus.OPEN, index=True)
    title = Column(String(400), nullable=False)
    site_url = Column(Text, nullable=True)          # URL where bug was found
    area = Column(String(200), nullable=True)        # e.g. "Admin Panel > Finance"
    steps_to_reproduce = Column(Text, nullable=True)
    observed_behavior = Column(Text, nullable=True)
    expected_behavior = Column(Text, nullable=True)
    analysis = Column(Text, nullable=True)           # Agent's diagnosis
    screenshot_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    repo = relationship("Repo")
    filed_by = relationship("Agent")
    task = relationship("Task")


class SecretKey(Base):
    """
    Encrypted credential vault entry.

    Security model:
    - `encrypted_value` is AES-encrypted via Fernet, key derived from the unlock key + salt
    - `salt` is a random 16-byte value encoded as base64 — stored, safe to expose
    - The unlock key is NEVER stored anywhere. Only the human knows it.
    - An agent must supply the unlock key at reveal-time to decrypt.
    - Wrong unlock key → decryption fails → 403 returned.
    """
    __tablename__ = "secret_keys"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    repo_id = Column(UUID(as_uuid=False), ForeignKey("repos.id"), nullable=True)  # optional repo association
    created_by_id = Column(UUID(as_uuid=False), ForeignKey("agents.id"))
    label = Column(String(200), nullable=False)          # e.g. "Production Postgres"
    description = Column(Text, nullable=True)            # what this key is for
    key_type = Column(String(50), default="DATABASE")    # DATABASE | API_KEY | SSH | OTHER
    encrypted_value = Column(Text, nullable=False)       # Fernet-encrypted credential
    salt = Column(String(100), nullable=False)           # base64-encoded random salt
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed_at = Column(DateTime, nullable=True)   # audit: when was it last revealed
    last_accessed_by_id = Column(UUID(as_uuid=False), nullable=True)  # audit: who last revealed it

    repo = relationship("Repo")
    created_by = relationship("Agent", foreign_keys=[created_by_id])


class Setting(Base):
    """
    Global system settings (e.g., GitHub Token, Admin email, etc.)
    Stored as key-value pairs.
    """
    __tablename__ = "settings"
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

