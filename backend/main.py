"""
FastAPI entrypoint for the Workflow Web UI.

Single-port architecture:
  - API routes under /api/*
  - Built frontend (frontend/dist/) served as static files at /
  - SPA fallback: all non-API paths serve index.html

Usage (production):
  cd frontend && npm run build
  cd ../backend && python3 main.py
  → http://localhost:8000

Usage (dev, with hot-reload):
  cd frontend && npm run dev    (port 5173, proxies /api → 8000)
  cd ../backend && python3 main.py
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from starlette.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from sqlmodel import Session, select, desc

from config import settings
from database import create_db_and_tables, engine
from models import Project, Task
from schemas import (
    ProjectCreate, ProjectOut, ProjectListItem, TaskOut,
    DebugRequest, DebugResponse, TestGenerateRequest, AnswerRequest,
)
from worker import run_workflow, debug_analyze, generate_test_instruction, generate_tool_instruction, pause_events

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("main")

# ─── Frontend dist path ──────────────────────────────────────
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

# ─── Streaming queues per project ────────────────────────────
stream_queues: dict[str, asyncio.Queue] = {}



# ─── Lifespan ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — creating DB tables…")
    create_db_and_tables()
    dist_ok = FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists()
    if dist_ok:
        logger.info(f"Frontend dist found at {FRONTEND_DIST}")
    else:
        logger.warning(
            "Frontend dist not found. Run: cd frontend && npm run build"
        )
    yield
    logger.info("Shutting down")


# ─── App ─────────────────────────────────────────────────────

app = FastAPI(
    title="Workflow Web UI",
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Helpers ─────────────────────────────────────────────────

def _project_to_out(project: Project) -> ProjectOut:
    # pending_questions and user_answers are stored as JSON strings in DB;
    # make sure they are passed as proper strings (or None).
    pq = project.pending_questions
    ua = project.user_answers
    return ProjectOut(
        id=project.id,
        project_idea=project.project_idea,
        model=project.model,
        github_repo=project.github_repo,
        project_dir=project.project_dir,
        status=project.status,
        status_detail=project.status_detail,
        error=project.error,
        pending_questions=pq,
        user_answers=ua,
        prd=project.prd,
        architecture=project.architecture,
        plan=project.plan,
        created_at=project.created_at,
        updated_at=project.updated_at,
        tasks=[TaskOut.model_validate(t) for t in (project.tasks or [])],
    )


def _project_to_list(project: Project) -> ProjectListItem:
    return ProjectListItem(
        id=project.id,
        project_idea=project.project_idea,
        model=project.model,
        github_repo=project.github_repo,
        project_dir=project.project_dir,
        status=project.status,
        status_detail=project.status_detail,
        created_at=project.created_at,
    )


# ─── API Routes ──────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/projects", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectCreate):
    """Create a new project and launch the workflow in background."""
    with Session(engine) as session:
        project = Project(
            project_idea=body.project_idea,
            github_repo=body.github_repo,
            project_dir=body.project_dir,
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        project_id = project.id

    # Create streaming queue for this project
    queue: asyncio.Queue = asyncio.Queue()
    stream_queues[project_id] = queue

    # Launch background worker with streaming queue
    asyncio.create_task(run_workflow(
        project_id, body.project_idea,
        model=body.model, github_repo=body.github_repo,
        project_dir=body.project_dir,
        stream_queue=queue,
    ))

    with Session(engine) as session:
        p = session.get(Project, project_id)
        return _project_to_out(p)


@app.get("/api/projects", response_model=list[ProjectListItem])
async def list_projects():
    with Session(engine) as session:
        stmt = select(Project).order_by(desc(Project.created_at))
        projects = session.exec(stmt).all()
        return [_project_to_list(p) for p in projects]


@app.get("/api/projects/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str):
    with Session(engine) as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        project.tasks = session.exec(
            select(Task).where(Task.project_id == project_id)
        ).all()
        return _project_to_out(project)


@app.post("/api/projects/{project_id}/answer")
async def answer_project_questions(project_id: str, body: AnswerRequest):
    """Submit answers to the PM's soul-searching questions and resume workflow."""
    with Session(engine) as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if project.status != "awaiting_input":
            raise HTTPException(status_code=400, detail="Project is not awaiting input")

        # Save answers to DB and clear pending questions
        project.user_answers = json.dumps(body.answers, ensure_ascii=False)
        project.pending_questions = None  # ✅ 清空，防止前端重新打开时弹窗
        project.status = "running"
        project.status_detail = "🏗️ 继续架构设计中…（已收到回答）"
        project.updated_at = datetime.now(timezone.utc)
        session.add(project)
        session.commit()

    # Resume the paused worker
    event = pause_events.pop(project_id, None)
    if event:
        event.set()

    return {"ok": True, "message": f"已回答 {len(body.answers)} 个问题，继续架构设计"}


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and its tasks, clean up streaming resources."""
    # Clean up in-memory resources
    stream_queues.pop(project_id, None)
    pause_events.pop(project_id, None)

    with Session(engine) as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Delete tasks first (cascade should handle this, but be explicit)
        tasks = session.exec(select(Task).where(Task.project_id == project_id)).all()
        for t in tasks:
            session.delete(t)
        session.delete(project)
        session.commit()

    return {"ok": True, "message": "Project deleted"}


@app.get("/api/projects/{project_id}/stream")
async def stream_project(project_id: str, request: Request):
    """SSE endpoint for real-time workflow progress.

    Hybrid approach:
      - Reads streaming tokens from the project's asyncio.Queue (real-time)
      - Polls DB for state changes (full state snapshots)
      - Forward token/step_start/step_end events from the queue
      - Forward update/completed/failed events from DB polling
    """
    async def event_generator():
        last_updated = None
        queue = stream_queues.get(project_id)
        # Wait up to 3s per cycle for queue events before polling DB
        queue_timeout = 0.3 if queue else None

        def _dump() -> str:
            """Load project + tasks from DB in a single session and return JSON."""
            with Session(engine) as s:
                p = s.get(Project, project_id)
                if p is None:
                    return "{}"
                p.tasks = s.exec(
                    select(Task).where(Task.project_id == project_id)
                ).all()
                return json.dumps(
                    _project_to_out(p).model_dump(mode="json"),
                    ensure_ascii=False,
                )

        while True:
            if await request.is_disconnected():
                break

            # ── Step 1: Drain queue events (real-time streaming) ──
            if queue is not None:
                try:
                    while True:
                        event = await asyncio.wait_for(queue.get(), timeout=queue_timeout)
                        yield event
                        if event.get("event") in ("completed", "failed"):
                            return
                except asyncio.TimeoutError:
                    pass

            # ── Step 2: Poll DB for state changes ──
            with Session(engine) as session:
                project = session.get(Project, project_id)
                if project is None:
                    yield {"event": "error", "data": "Project deleted"}
                    break

                if project.updated_at != last_updated:
                    data = _dump()
                    yield {"event": "update", "data": data}
                    last_updated = project.updated_at

                if project.status == "completed":
                    data = _dump()
                    yield {"event": "completed", "data": data}
                    stream_queues.pop(project_id, None)
                    break
                if project.status == "failed":
                    data = _dump()
                    yield {"event": "failed", "data": data}
                    stream_queues.pop(project_id, None)
                    break

            # Brief pause between cycles (only if no queue active)
            if queue is None:
                await asyncio.sleep(0.8)

    return EventSourceResponse(event_generator())


@app.post("/api/debug")
async def debug(body: DebugRequest) -> DebugResponse:
    """分析报错日志，返回 BUG 调试结果。支持关联项目上下文。"""
    project_context = ""
    if body.project_id:
        with Session(engine) as session:
            project = session.get(Project, body.project_id)
            if project and project.prd:
                # 提取前 500 字作为项目背景
                project_context = (
                    f"项目背景：{project.project_idea[:200]}\n"
                    f"技术架构摘要：{(project.architecture or '')[:300]}"
                )
    result = await debug_analyze(
        body.error_log,
        code_context=body.code_context,
        project_context=project_context,
    )
    return DebugResponse(**result)


@app.post("/api/test-generate")
async def test_generate(body: TestGenerateRequest):
    """生成测试指令。支持关联项目上下文和组合提示词③/⑤。"""
    project_context = ""
    if body.project_id:
        with Session(engine) as session:
            project = session.get(Project, body.project_id)
            if project:
                project_context = (
                    f"项目：{project.project_idea[:200]}\n"
                    f"架构：{(project.architecture or '')[:300]}"
                )
    instruction = await generate_test_instruction(
        scenario=body.scenario,
        project_context=project_context,
        with_audit=body.with_audit,
        with_design=body.with_design,
    )
    return {"instruction": instruction}


@app.post("/api/tool-generate")
async def tool_generate(body: dict):
    """统一工具生成接口：审计(audit) / 设计(design)。"""
    tool = body.get("tool", "")
    input_text = body.get("input", "")
    tech_stack = body.get("tech_stack")
    project_id = body.get("project_id")

    project_context = ""
    if project_id:
        with Session(engine) as session:
            project = session.get(Project, project_id)
            if project:
                project_context = f"项目：{project.project_idea[:200]}\n架构：{(project.architecture or '')[:300]}"

    instruction = await generate_tool_instruction(
        tool=tool,
        input_text=input_text,
        project_context=project_context,
        tech_stack=tech_stack,
    )
    return {"instruction": instruction}


# ─── SPA fallback (must be last) ────────────────────────────


def _frontend_ok() -> bool:
    """Check if frontend dist is available."""
    return FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists()


if _frontend_ok():
    # Mount static assets
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")


@app.get("/")
async def serve_root():
    """Serve the SPA entry point."""
    if not _frontend_ok():
        return JSONResponse(
            status_code=503,
            content={"detail": "Frontend not built. Run: cd frontend && npm run build"},
        )
    return FileResponse(str(FRONTEND_DIST / "index.html"))


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve frontend files with SPA fallback to index.html."""
    if not _frontend_ok():
        return JSONResponse(
            status_code=503,
            content={"detail": "Frontend not built. Run: cd frontend && npm run build"},
        )
    file_path = FRONTEND_DIST / full_path
    if file_path.is_file():
        return FileResponse(str(file_path))
    # SPA fallback: serve index.html for any non-file path
    return FileResponse(str(FRONTEND_DIST / "index.html"))


# ─── Entrypoint ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
