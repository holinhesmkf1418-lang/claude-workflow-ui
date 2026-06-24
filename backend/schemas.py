from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    project_idea: str
    model: Optional[str] = None  # 模型选择，None 表示用 .env 默认


class TaskOut(BaseModel):
    id: int
    task_id: str
    title: str
    phase: str
    description: Optional[str] = None
    goal: str
    requirements: str
    constraints: Optional[str] = None
    acceptance: str
    codex_instruction: str

    class Config:
        from_attributes = True


class ProjectOut(BaseModel):
    id: str
    project_idea: str
    model: Optional[str] = None
    status: str
    status_detail: str
    error: Optional[str] = None
    prd: Optional[str] = None
    architecture: Optional[str] = None
    plan: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tasks: list[TaskOut] = []

    class Config:
        from_attributes = True


class ProjectListItem(BaseModel):
    id: str
    project_idea: str
    model: Optional[str] = None
    status: str
    status_detail: str
    created_at: datetime

    class Config:
        from_attributes = True


class DebugRequest(BaseModel):
    error_log: str
    code_context: Optional[str] = None


class DebugResponse(BaseModel):
    state: str
    root_cause: str
    risk: str = ""
    machine_instruction: str
    explanation: str = ""
    raw: str = ""
