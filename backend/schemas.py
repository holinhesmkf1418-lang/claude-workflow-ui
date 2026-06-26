from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    project_idea: str
    model: Optional[str] = None
    github_repo: Optional[str] = None
    project_dir: Optional[str] = None


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
    github_repo: Optional[str] = None
    project_dir: Optional[str] = None
    pending_questions: Optional[str] = None  # JSON array of questions
    user_answers: Optional[str] = None       # JSON object
    prd: Optional[str] = None
    architecture: Optional[str] = None
    plan: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tasks: list[TaskOut] = []

    class Config:
        from_attributes = True


class AnswerRequest(BaseModel):
    answers: dict[str, str]  # { "0": "answer text", "1": "..." }


class ProjectListItem(BaseModel):
    id: str
    project_idea: str
    model: Optional[str] = None
    github_repo: Optional[str] = None
    status: str
    status_detail: str
    created_at: datetime

    class Config:
        from_attributes = True


class DebugRequest(BaseModel):
    error_log: str
    code_context: Optional[str] = None
    project_id: Optional[str] = None


class DebugResponse(BaseModel):
    state: str
    root_cause: str
    risk: str = ""
    machine_instruction: str
    explanation: str = ""
    raw: str = ""


class TestGenerateRequest(BaseModel):
    scenario: str
    project_id: Optional[str] = None
    with_audit: bool = False
    with_design: bool = False
