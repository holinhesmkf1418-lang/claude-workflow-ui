export const meta = {
  name: 'start-new-project',
  description: '三步走：需求推演 → 系统架构 → 开发计划，产出 Codex 就绪的 Task 指令',
  phases: [
    { title: '需求推演', detail: '补全隐性需求，输出结构化 PRD' },
    { title: '架构设计', detail: '技术选型 + 数据模型 + claude.md 红线' },
    { title: '生成计划', detail: '可勾选清单 + Codex 就绪指令文件' },
  ],
}

// ─── 解析参数 ──────────────────────────────────────
const projectIdea = typeof args === 'string' ? args : args.projectIdea
const ctx = typeof args === 'object' ? args : {}
const projectContext = {
  projectDir: ctx.projectDir || './',
  githubRepo: ctx.githubRepo || '',
  dbPath: ctx.dbPath || '',
  frontendDir: ctx.frontendDir || 'frontend/',
  backendDir: ctx.backendDir || 'backend/',
}

// ─── 第 1 步：需求推演 ──────────────────────────────
phase('需求推演')
const prd = await agent(`
你是资深业务架构师与高级产品经理。
用户的项目想法：${projectIdea}

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
`)

// ─── 第 2 步：系统架构设计 ──────────────────────────
phase('架构设计')
const architecture = await agent(`
你是高级系统架构师。
基于以下 PRD 设计系统架构：

${prd}

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

用代码框 \`\`\`markdown 包裹这段 claude.md。

**## 3. 架构师的深度思考**
- 2-3 个技术风险点及预备方案
`)

// ─── 从架构输出中提取 claude.md ───────────────────
// 架构输出包含一段 ```markdown ... ``` 的 claude.md
// 我们把它连同项目上下文一起传给第 3 步

// ─── 第 3a 步：生成人工可读的开发计划 ────────────
phase('生成计划')
const plan = await agent(`
你是首席技术架构师与敏捷交付管理专家。
基于以下内容，制定结构化开发计划。

## PRD
${prd}

## 架构设计
${architecture}

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
`)

// ─── 从架构输出中提取家规 ──────────────────────────
const clanRules = architecture.replace(/.*?(?=###|##)/s, '').trim()
// 尝试提取 ```markdown ... ``` 中的 claude.md 内容
const m = clanRules.match(/```markdown\n?([\s\S]*?)\n?```/)
const clanMd = m ? m[1].trim() : clanRules.slice(0, 500)

// ─── 第 3b 步：生成轻量 Task 元数据 ──────────────
phase('生成任务清单')
const TASK_SCHEMA = {
  type: 'object',
  properties: {
    tasks: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          phase: { type: 'string' },
          description: { type: 'string' },
          goal: { type: 'string' },
          requirements: { type: 'string' },
          constraints: { type: 'string' },
          acceptance: { type: 'string' },
        },
        required: ['id', 'title', 'phase', 'goal', 'requirements', 'acceptance'],
      },
    },
  },
}

const tasksData = await agent(`
你是一个任务分解专家。基于以下开发计划，输出每个 Task 的元数据。

## 开发计划
${plan}

每个 Task 输出：
- goal：目标（一句话）
- requirements：具体要求（字段定义、接口、业务规则）
- constraints：关键约束
- acceptance：验收标准

注意：只输出该 Task 独有的内容，不要重复项目上下文和家规。
`, { schema: TASK_SCHEMA })

// ─── 组装完整 codex_instruction ───────────────────
const workRules = `# 工作要求
1. 所有代码写在项目目录下对应子目录，不要在别的地方创建文件
2. 每完成一个阶段性成果就提交 git，commit 格式：TaskX.X: 描述
3. 遇到模糊需求先列出选项问我，不要猜测
4. 只写当前任务需要的最少代码，不过度设计
5. 严格执行家规中的绝对红线
6. 需要的依赖自行安装，不要让我手动装`

const projectHeader = `# 项目上下文
项目目录：${projectContext.projectDir}${projectContext.githubRepo ? `\nGitHub仓库：${projectContext.githubRepo}` : ''}
前端目录：${projectContext.frontendDir}
后端目录：${projectContext.backendDir}${projectContext.dbPath ? `\n数据库文件：${projectContext.dbPath}` : ''}`

const tasks = (tasksData?.tasks || []).map((t) => ({
  id: t.id,
  title: t.title,
  phase: t.phase,
  description: t.description || t.goal,
  codex_instruction: [
    projectHeader,
    '',
    workRules,
    '',
    `# 家规\n${clanMd}`,
    '',
    `# 本次任务：Task ${t.id} ${t.title}`,
    '',
    `## 目标\n${t.goal}`,
    `## 具体要求\n${t.requirements}`,
    t.constraints ? `## 关键约束\n${t.constraints}` : '',
    `## 验收标准\n${t.acceptance}`,
  ]
    .filter(Boolean)
    .join('\n'),
}))

// ─── 返回结果（含结构化 Task 数据）─────────────────
return {
  prd,
  architecture,
  plan,
  tasks,
  summary: {
    phase1: '✅ 需求推演完成 — PRD 已输出',
    phase2: '✅ 架构设计完成 — claude.md 红线已生成',
    phase3: `✅ 开发计划完成 — ${tasks.length} 个 Codex 就绪任务已生成`,
  },
}
