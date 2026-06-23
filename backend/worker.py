"""
Three-step agent pipeline (DeepSeek backend):
1. PRD (Product Requirements Document)
2. System Architecture Design
3. Development Plan + Structured Task Extraction
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional, List

from openai import AsyncOpenAI
from sqlmodel import Session, select

from config import settings
from database import engine
from models import Project, Task

logger = logging.getLogger("worker")

# ─── DeepSeek client ──────────────────────────────────────
_client: Optional[AsyncOpenAI] = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return _client


# ─── Prompt templates (mirror the Workflow) ──────────────────

PRD_PROMPT = """你是资深业务架构师与高级产品经理。
用户的项目想法：{project_idea}

请严格按以下结构输出：

**0. PM 的需求洞察与重构**
- 用户原始意图
- AI 深度推演与补全（补充了哪些他没想到但必须有的模块）

**1. 产品全局定义**
- 产品定位（一句话）
- 目标用户与核心场景
- 业务目标

**2. 业务架构与状态流转**
- 核心子系统组成
- 核心主流程（步骤化）
- 关键状态机

**3. 详细功能矩阵（表格）**
| 模块 | 子功能 | 功能描述 | 核心规则 | 异常处理 | 优先级 |

要求：所有业务规则高度可配置化，避免硬编码。

**4. 非功能性与扩展性需求**

**5. PM 的灵魂追问（3-5 个）**
"""

ARCH_PROMPT = """你是高级系统架构师。
基于以下 PRD 设计系统架构：

{prd}

输出以下内容，请用明确的 Markdown 标题分隔：

**## 1. 核心架构设计与技术选型**
- 技术栈选型理由
- 用 Mermaid 绘制核心实体关系图
- 关键表结构说明（体现配置化思维）

**## 2. 项目专属 claude.md**
输出一段 300 字以内的 Markdown，包含：
- 技术栈
- 绝对红线（零硬编码、数据层级完整、严禁静默失败、模块化强制）
- 编程行为约束

用代码框 ```markdown 包裹这段 claude.md。

**## 3. 架构师的深度思考**
- 2-3 个技术风险点及预备方案
"""

PLAN_PROMPT = """你是首席技术架构师与敏捷交付管理专家。
基于以下内容，制定结构化开发计划。

## PRD
{prd}

## 架构设计
{architecture}

## 前置自检（必须执行）
1. 反巨石文件：是否有组件/文件堆砌过多逻辑？
2. 反硬编码：是否有业务规则直接写死在代码中？
3. 数据层级：多级数据流转时父级标识是否确保保留？
4. 并发风险：耗时任务是否缺失异步解耦方案？

## 输出格式

预执行自检报告：（3-4 句话）

结构化开发计划（按 Phase 1-4 组织，使用 [ ] 语法）：
- Phase 1：基建与数据模型
  - Task 1.1：...
  - Task 1.2：...
- Phase 2：后端核心逻辑与 API
- Phase 3：前端视图与交互闭环
- Phase 4：测试与联调验证

启动命令.md：（完整的前后端启动命令）
"""

EXTRACT_TASKS_PROMPT = """你是一个任务分解专家。基于以下开发计划，输出每个 Task 的元数据。

## 开发计划
{plan}

每个 Task 输出以下字段（JSON 格式）：
- id: 任务编号，如 "1.1"
- title: 任务标题
- phase: 所属 Phase，如 "Phase 1：基建与数据模型"
- description: 简要描述
- goal: 目标（一句话）
- requirements: 具体要求（字段定义、接口、业务规则）
- constraints: 关键约束（没有则留空）
- acceptance: 验收标准

输出格式必须是严格的 JSON：{{"tasks": [{{"id": "...", "title": "...", ...}}]}}
注意：只输出该 Task 独有的内容，不要重复项目上下文和家规。
"""

# ─── Work rules (appended to each codex_instruction) ────────

WORK_RULES = """# 工作要求
1. 所有代码写在项目目录下对应子目录，不要在别的地方创建文件
2. 每完成一个阶段性成果就提交 git，commit 格式：TaskX.X: 描述
3. 遇到模糊需求先列出选项问我，不要猜测
4. 只写当前任务需要的最少代码，不过度设计
5. 严格执行家规中的绝对红线
6. 需要的依赖自行安装，不要让我手动装"""


# ─── Helpers ─────────────────────────────────────────────────

async def call_llm(prompt: str, *, model: Optional[str] = None, max_tokens: int = 8192) -> str:
    """Call DeepSeek with a plain-text prompt, return the text response."""
    client = get_client()
    resp = await client.chat.completions.create(
        model=model or settings.deepseek_model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


async def extract_tasks_structured(plan: str, *, model: Optional[str] = None) -> List[dict]:
    """Call DeepSeek with json_object response_format to extract structured task data."""
    client = get_client()
    resp = await client.chat.completions.create(
        model=model or settings.deepseek_model,
        max_tokens=8192,
        messages=[{"role": "user", "content": EXTRACT_TASKS_PROMPT.format(plan=plan)}],
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
        tasks = data.get("tasks", [])
        if tasks:
            return tasks
        logger.warning(f"extract_tasks: no tasks key in response, keys: {list(data.keys())}")
    except json.JSONDecodeError as e:
        logger.error(f"extract_tasks: JSON parse error: {e}")
    return []


def extract_claude_md(architecture: str) -> str:
    """Extract the ```markdown ... ``` block from architecture output."""
    m = re.search(r"```markdown\n?(.*?)\n?```", architecture, re.DOTALL)
    if m:
        return m.group(1).strip()
    return architecture[:500]


def assemble_codex_instruction(
    task: dict,
    project_header: str,
    clan_md: str,
) -> str:
    """Assemble the complete Codex-ready instruction for one task."""
    parts = [
        project_header,
        "",
        WORK_RULES,
        "",
        f"# 家规\n{clan_md}",
        "",
        f"# 本次任务：Task {task['id']} {task['title']}",
        "",
        f"## 目标\n{task['goal']}",
        f"## 具体要求\n{task['requirements']}",
    ]
    if task.get("constraints"):
        parts.append(f"## 关键约束\n{task['constraints']}")
    parts.append(f"## 验收标准\n{task['acceptance']}")
    return "\n".join(parts)


def update_project_in_db(project_id: str, **kwargs):
    """Synchronously update a project record."""
    with Session(engine) as session:
        project = session.get(Project, project_id)
        if project is None:
            logger.error(f"Project {project_id} not found for update")
            return
        for k, v in kwargs.items():
            setattr(project, k, v)
        project.updated_at = datetime.now(timezone.utc)
        session.add(project)
        session.commit()


# ─── Main workflow ───────────────────────────────────────────

async def run_workflow(project_id: str, project_idea: str, model: Optional[str] = None):
    """
    Run the 3-step workflow as a background async task.

    Steps:
      1. PRD generation
      2. Architecture design
      3a. Development plan
      3b. Structured task extraction
    """
    logger.info(f"[{project_id}] Workflow started: {project_idea[:60]}...")

    # Save selected model to project record
    if model:
        update_project_in_db(project_id, model=model)

    try:
        # ── Step 1: PRD ────────────────────────────────────
        update_project_in_db(project_id, status="running", status_detail="需求推演中…")
        logger.info(f"[{project_id}] Step 1/4: PRD generation ({model or 'default'})")
        prd = await call_llm(PRD_PROMPT.format(project_idea=project_idea), model=model)
        update_project_in_db(project_id, prd=prd, status_detail="✅ 需求推演完成")

        # ── Step 2: Architecture ────────────────────────────
        update_project_in_db(project_id, status_detail="架构设计中…")
        logger.info(f"[{project_id}] Step 2/4: Architecture design")
        architecture = await call_llm(ARCH_PROMPT.format(prd=prd), model=model)
        update_project_in_db(project_id, architecture=architecture, status_detail="✅ 架构设计完成")

        # ── Step 3a: Development Plan ──────────────────────
        update_project_in_db(project_id, status_detail="生成开发计划中…")
        logger.info(f"[{project_id}] Step 3/4: Development plan")
        plan = await call_llm(PLAN_PROMPT.format(prd=prd, architecture=architecture), model=model)
        update_project_in_db(project_id, plan=plan, status_detail="✅ 开发计划完成")

        # ── Step 3b: Structured Tasks ──────────────────────
        update_project_in_db(project_id, status_detail="提取 Task 清单中…")
        logger.info(f"[{project_id}] Step 4/4: Task extraction")
        raw_tasks = await extract_tasks_structured(plan, model=model)

        # ── Assemble task records ─────────────────────────
        clan_md = extract_claude_md(architecture)
        project_header = f"# 项目上下文\n项目想法：{project_idea}"

        with Session(engine) as session:
            db_project = session.get(Project, project_id)
            if db_project:
                existing = session.exec(
                    select(Task).where(Task.project_id == project_id)
                ).all()
                for t in existing:
                    session.delete(t)

                for t in raw_tasks:
                    codex_inst = assemble_codex_instruction(t, project_header, clan_md)
                    task = Task(
                        project_id=project_id,
                        task_id=t["id"],
                        title=t["title"],
                        phase=t.get("phase", ""),
                        description=t.get("description", t.get("goal", "")),
                        goal=t["goal"],
                        requirements=t["requirements"],
                        constraints=t.get("constraints"),
                        acceptance=t["acceptance"],
                        codex_instruction=codex_inst,
                    )
                    session.add(task)
                session.commit()

        update_project_in_db(
            project_id,
            status="completed",
            status_detail=f"✅ 完成 — 共 {len(raw_tasks)} 个 Codex 就绪任务",
        )
        logger.info(
            f"[{project_id}] Workflow completed — {len(raw_tasks)} tasks generated"
        )

    except Exception as e:
        logger.exception(f"[{project_id}] Workflow failed")
        update_project_in_db(
            project_id,
            status="failed",
            status_detail="❌ Workflow 执行失败",
            error=str(e),
        )
