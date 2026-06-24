# Workflow Web UI

给 Claude Code 全局 Workflow 的大脑可视化面板。遵循「双脑工作流」SOP：

- **大脑**（本工具）：做规划、出方案、生成指令
- **小脑**（Codex 桌面版）：粘贴指令执行代码

## 🧰 工具一览

| 页面 | 提示词 | 用途 |
|---|---|---|
| **首页 / 新建项目** | ① ② ⑦ | 输入项目想法 → 自动跑 PRD → 架构 → 开发计划 + Task 清单 |
| **🐛 调试** | ④ | 贴报错日志 → 大脑分析根因 → 出精准修复指令 |
| **🧪 测试** | ⑥ | 描述测试场景 → 出完整 Playwright 指令 → 可选附加审计/设计规范 |
| **🔍 审计** | ③ | 贴代码 → 扫描巨石文件、硬编码、静默失败 |
| **🎨 设计** | ⑤ | 描述页面需求 → 生成 Linear/Apple 质感的前端指令 |

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Element Plus + Pinia + Vite |
| 后端 | FastAPI + SQLModel + SQLite |
| AI | DeepSeek（OpenAI 兼容协议）|

## 快速开始（单端口）

```bash
# 1. 安装后端依赖
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 2. 构建前端
cd ../frontend
npm install
npm run build

# 3. 启动服务
cd ../backend
python3 main.py
# → http://localhost:8000
```

### 开发模式（带热重载）

```bash
# 终端 1：后端
cd backend && python3 main.py

# 终端 2：前端（自动代理 /api → 8000）
cd frontend && npm run dev
# → http://localhost:5173
```

## 项目结构

```
claude-workflow-ui/
├── backend/
│   ├── main.py          # FastAPI 入口 + 5 个 API 路由 + SSE + 静态文件
│   ├── worker.py        # Agent 流水线 + 5 个提示词引擎
│   ├── models.py        # SQLModel 数据模型
│   ├── schemas.py       # Pydantic 请求/响应模型
│   ├── config.py        # 环境变量配置
│   └── database.py      # SQLite 连接
├── frontend/
│   └── src/
│       ├── views/
│       │   ├── NewProject.vue      # 首页：启动新项目
│       │   ├── ProjectResult.vue   # 项目结果展示
│       │   ├── DebugPanel.vue      # 🐛 BUG 调试
│       │   ├── TestGenerator.vue   # 🧪 测试生成
│       │   ├── AuditPanel.vue      # 🔍 代码审计
│       │   └── DesignTool.vue      # 🎨 设计规范
│       └── components/
│           ├── StatusTimeline.vue   # 进度时间线
│           ├── PrdViewer.vue        # PRD 渲染
│           ├── ArchitectureViewer.vue # 架构渲染
│           └── TaskListView.vue     # Task 清单 + 一键复制
├── docs/                          # SOP 文档
│   ├── ai-coding-sop.md           # 完整方法论
│   ├── brain-vs-coder.md          # 大脑小脑分工图
│   ├── red-lines.md               # 四条保命红线
│   └── prompts/                   # 七个提示词全文
└── workflow/
    └── start-new-project.ts       # 原始 Workflow 脚本
```

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/projects` | 创建项目并启动 Workflow |
| GET | `/api/projects` | 项目列表 |
| GET | `/api/projects/{id}` | 项目详情（含 Task） |
| GET | `/api/projects/{id}/stream` | SSE 实时进度 |
| POST | `/api/debug` | BUG 调试分析 |
| POST | `/api/test-generate` | 生成测试指令 |
| POST | `/api/tool-generate` | 审计 / 设计指令生成 |

## 与原始 Workflow 的关系

后端 `worker.py` 用 DeepSeek API **重新实现了** `start-new-project.ts` 的三步流水线，提示词一致。同时扩展了调试、测试、审计、设计四个工具，覆盖 SOP 全流程。
