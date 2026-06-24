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
            timeout=120.0,
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

# ─── BUG 调试提示词（原始提示词④的完整复现）────────────

DEBUG_PROMPT = """Role：极度追求上下文压缩与执行精度的 claude/codex 调度引擎。

核心戒律（Token & Precision Directives）：
1. 极致压缩：生成的给 IDE 的指令必须剥离所有礼貌用语与背景废话。强制要求 IDE "No yapping"、"Diff only"。
2. 精准定标：在 PROBE 态必须强制 IDE 先输出要修改的函数名或行号区间，绝不允许盲目重写动辄数百行的组件。
3. 根因与配置红线：严格防范 IDE 为了图快而硬编码业务逻辑。必须要求其排查数据流源头，优先复用或增加动态配置。

分析用户提供的报错日志和项目上下文，输出 JSON：

{{
  "state": "PROBE" 或 "SURGERY" 或 "GATE" 或 "VERIFY",
  "root_cause": "一句话指出根本原因（不超过 30 字）",
  "risk": "潜在的上下文断裂风险或跨模块影响",
  "machine_instruction": "给 Codex 的完整机器指令，必须遵从下方格式",
  "explanation": "对当前状态和所需操作的简要说明"
}}

State Machine 说明：
- [PROBE]：缺位。需指令 IDE 使用 grep/AST 搜索特定变量、组件或路由。
- [SURGERY]：锁定。生成高限制性的局部修复指令。
- [GATE]：风险。IDE 的提议涉及跨模块、依赖变更或全文件重构，需拦截并给出 (Y/N) 建议。
- [VERIFY]：完结。生成回归测试边界。

machine_instruction 的格式要求（若非完结态，必须按此结构输出）：
@文件路径 (必须精确到具体文件，拒绝 @Codebase 漫游)
[TARGET]
明确指出要修改的函数、接口或 CSS 变量。
[CONSTRAINTS]
- 行为锁定：禁止修改原有样式 / 保持现有的响应式追踪方式。
- 红线：绝对禁止硬编码业务规则；确保数据解析时层级融合不丢失。
- 格式化：No explanations. ONLY output the code diff or specific function replacement. DO NOT output the whole file.
[ACTION]
1. (探针检索/代码替换步骤 1)
2. (探针检索/代码替换步骤 2)

## 项目上下文（关联项目信息，用于精准定位）
{project_context}

## 报错日志
{error_log}

## 代码上下文
{code_context}
"""


async def debug_analyze(error_log: str, code_context: Optional[str] = None, project_context: Optional[str] = None) -> dict:
    """分析报错日志，返回结构化调试结果。"""
    client = get_client()
    prompt = DEBUG_PROMPT.format(
        error_log=error_log,
        code_context=code_context or "无",
        project_context=project_context or "无",
    )
    resp = await client.chat.completions.create(
        model=settings.deepseek_model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
        return {
            "state": data.get("state", "PROBE"),
            "root_cause": data.get("root_cause", "无法分析"),
            "risk": data.get("risk", ""),
            "machine_instruction": data.get("machine_instruction", ""),
            "explanation": data.get("explanation", ""),
            "raw": content,
        }
    except json.JSONDecodeError:
        return {
            "state": "PROBE",
            "root_cause": "JSON 解析失败，请重试",
            "risk": "",
            "machine_instruction": content,
            "explanation": "原始输出未按 JSON 格式返回，已展示原文",
            "raw": content,
        }


# ─── 测试生成提示词（提示词⑥ + 可选组合③⑤）────────────

TEST_PROMPT = """你是高级浏览器自动化与自愈执行专家。你的核心任务是基于需求编写并执行 Playwright 自动化测试脚本。

## 测试场景
{scenario}

## 项目上下文
{project_context}

## 输出要求
请输出一份完整的、可直接粘贴到 Codex 执行的测试指令，包含：

1. **测试分析与策略**：分析测试目标、关键交互路径、需拦截的 API 请求
2. **Playwright 测试脚本**：完整可执行的测试代码
3. **健壮性要求**：
   - 禁止 `page.waitForTimeout()` 等硬编码等待，使用基于状态的等待
   - 优先使用语义化选择器（Aria-labels、data-testid）
   - 必须包含异常处理与自愈逻辑（失败时分析 DOM 自动调整）
4. **自愈闭环**：脚本失败时捕获截图/DOM 快照 → 分析根因 → 调整策略重试
{audit_section}
{design_section}
"""

AUDIT_SECTION = """
## 附加：测试完成后执行代码审计
测试通过后，对本次修改涉及的文件执行代码审计：
1. 检查是否有超过 400 行的巨石组件或文件，如有则要求拆分
2. 检查是否有业务逻辑硬编码（正则、状态字典、阈值写死在代码中）
3. 检查是否有 `try-catch pass` 等静默失败逻辑
4. 检查多层级数据处理时是否有父级标识丢失
"""

DESIGN_SECTION = """
## 附加：应用前端设计规范
测试涉及前端 UI 时，确保：
1. 采用极简风格，善用留白，使用弥散阴影 + 1px 微妙边框
2. 所有颜色/间距/圆角提取为 CSS Variables
3. Hover/Active/Focus 状态有平滑过渡动画
4. 响应式布局，移动端优雅降级
"""


async def generate_test_instruction(
    scenario: str,
    project_context: Optional[str] = None,
    with_audit: bool = False,
    with_design: bool = False,
) -> str:
    """生成测试指令（提示词⑥ + 可选组合③或⑤）。"""
    prompt = TEST_PROMPT.format(
        scenario=scenario,
        project_context=project_context or "无",
        audit_section=AUDIT_SECTION if with_audit else "",
        design_section=DESIGN_SECTION if with_design else "",
    )
    return await call_llm(prompt, max_tokens=8192)


# ─── 审计提示词（提示词③精简版）────────────────────────

AUDIT_PROMPT = """你是代码审计专家。审查用户提供的代码，按以下维度输出审计结果：

## 审查维度
1. **结构与模块化**：是否有超过 400 行的巨石文件？是否需要拆分？
2. **零硬编码**：是否有业务规则、正则、状态值直接写死在代码中？
3. **静默失败**：是否有 try-catch pass 等吞错误的逻辑？
4. **数据层级**：多层级数据处理时是否有父级标识丢失？
5. **性能陷阱**：是否有循环内查询数据库或阻塞异步等操作？

## 用户输入
{input}

## 项目上下文
{project_context}

输出格式：列出发现问题，附上文件/行号建议，给出修复方向。不要输出完整代码，只给审计报告。
"""


# ─── 前端设计提示词（提示词⑤精简版）──────────────────────

DESIGN_PROMPT = """你是资深前端指令翻译官 & UI/UX 品控专家。

## 核心美学法则
- 空间与克制：善用留白，宽绰 Padding
- 光影：极轻微弥散阴影 + 1px 微妙边框
- 色彩：使用高级中性色阶，强调色内敛
- 微交互：所有状态切换伴随平滑过渡
- 绝对变量化：所有颜色/间距/圆角提取为 CSS Variables

## 用户需求
{input}

## 技术栈
{tech_stack}

输出格式：直接输出一份给 Codex 执行的完整前端指令，包含 DOM 结构、CSS 变量定义、微交互动画、响应式策略。对标 Linear/Apple 品质。
"""


async def generate_tool_instruction(
    tool: str,
    input_text: str,
    project_context: Optional[str] = None,
    tech_stack: Optional[str] = None,
) -> str:
    """生成审计(③)或设计(⑤)指令。"""
    if tool == "audit":
        prompt = AUDIT_PROMPT.format(input=input_text, project_context=project_context or "无")
    elif tool == "design":
        prompt = DESIGN_PROMPT.format(input=input_text, tech_stack=tech_stack or "Vue 3 + TypeScript + Element Plus")
    else:
        raise ValueError(f"Unknown tool: {tool}")
    return await call_llm(prompt, max_tokens=8192)


# ─── Work rules (appended to each codex_instruction) ────────

WORK_RULES = """# 工作要求
1. 所有代码写在项目目录下对应子目录，不要在别的地方创建文件
2. 每完成一个阶段性成果就提交 git，commit 格式：TaskX.X: 描述
3. 遇到模糊需求先列出选项问我，不要猜测
4. 只写当前任务需要的最少代码，不过度设计
5. 严格执行家规中的绝对红线
6. 需要的依赖自行安装，不要让我手动装"""


# ─── Helpers ─────────────────────────────────────────────────

async def call_llm(prompt: str, *, model: Optional[str] = None, max_tokens: int = 8192, max_retries: int = 3) -> str:
    """Call DeepSeek with retry on transient errors. 3 retries with exponential backoff."""
    last_error = None
    for attempt in range(max_retries):
        try:
            client = get_client()
            resp = await client.chat.completions.create(
                model=model or settings.deepseek_model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                timeout=120,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
                logger.warning(f"LLM call failed (attempt {attempt+1}): {e}, retrying in {wait}s")
                await asyncio.sleep(wait)
    logger.error(f"LLM call failed after {max_retries} attempts: {last_error}")
    raise last_error  # type: ignore


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
