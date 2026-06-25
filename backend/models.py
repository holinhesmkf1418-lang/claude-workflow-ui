import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlmodel import SQLModel, Field, Relationship


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())[:8],
        primary_key=True,
    )
    project_idea: str = Field(max_length=10000)
    model: Optional[str] = Field(default=None, max_length=100)  # 使用的模型名
    github_repo: Optional[str] = Field(default=None, max_length=500)  # 远程仓库地址
    status: str = Field(default="pending")  # pending | running | awaiting_input | completed | failed
    status_detail: str = Field(default="")  # 当前步骤描述
    error: Optional[str] = Field(default=None, max_length=5000)

    # 交互式暂停：灵魂追问
    pending_questions: Optional[str] = Field(default=None, max_length=10000)  # JSON array of questions
    user_answers: Optional[str] = Field(default=None, max_length=10000)       # JSON object {q_idx: answer}

    prd: Optional[str] = Field(default=None, max_length=100000)
    architecture: Optional[str] = Field(default=None, max_length=100000)
    plan: Optional[str] = Field(default=None, max_length=100000)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    tasks: List["Task"] = Relationship(back_populates="project", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: int = Field(primary_key=True, sa_column_kwargs={"autoincrement": True})
    project_id: str = Field(foreign_key="projects.id")
    task_id: str = Field(max_length=20)       # e.g. "1.1"
    title: str = Field(max_length=200)
    phase: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=2000)
    goal: str = Field(max_length=2000)
    requirements: str = Field(max_length=10000)
    constraints: Optional[str] = Field(default=None, max_length=5000)
    acceptance: str = Field(max_length=5000)
    codex_instruction: str = Field(max_length=50000)

    project: Project = Relationship(back_populates="tasks")
