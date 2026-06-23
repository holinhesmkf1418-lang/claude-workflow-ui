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
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from starlette.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from sqlmodel import Session, select, desc

from config import settings
from database import create_db_and_tables, engine
from models import Project, Task
from schemas import ProjectCreate, ProjectOut, ProjectListItem, TaskOut
from worker import run_workflow

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("main")

# ─── Frontend dist path ──────────────────────────────────────
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


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
    return ProjectOut(
        id=project.id,
        project_idea=project.project_idea,
        model=project.model,
        status=project.status,
        status_detail=project.status_detail,
        error=project.error,
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
        project = Project(project_idea=body.project_idea)
        session.add(project)
        session.commit()
        session.refresh(project)
        project_id = project.id

    # Launch background worker
    asyncio.create_task(run_workflow(project_id, body.project_idea, model=body.model))

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


@app.get("/api/projects/{project_id}/stream")
async def stream_project(project_id: str, request: Request):
    """SSE endpoint for real-time workflow progress."""
    with Session(engine) as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

    async def event_generator():
        last_updated = None
        while True:
            if await request.is_disconnected():
                break

            with Session(engine) as session:
                project = session.get(Project, project_id)
                if project is None:
                    yield {"event": "error", "data": "Project deleted"}
                    break

                if project.updated_at != last_updated:
                    project.tasks = session.exec(
                        select(Task).where(Task.project_id == project_id)
                    ).all()
                    data = _project_to_out(project).model_dump(mode="json")
                    yield {"event": "update", "data": json.dumps(data, ensure_ascii=False)}
                    last_updated = project.updated_at

                if project.status == "completed":
                    yield {"event": "completed", "data": json.dumps(data, ensure_ascii=False)}
                    break
                if project.status == "failed":
                    yield {"event": "failed", "data": json.dumps(data, ensure_ascii=False)}
                    break

            await asyncio.sleep(0.8)

    return EventSourceResponse(event_generator())


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
