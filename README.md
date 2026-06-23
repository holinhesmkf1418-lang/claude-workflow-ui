# Workflow Web UI

给 Claude Code 全局 Workflow `start-new-project` 的可视化 Web 界面。

填表单（项目想法）→ 点按钮 → 后台跑 Workflow → 展示结果（PRD + 架构 + Task 清单）→ 每个 Task 可一键复制完整指令发给 Codex。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Element Plus + Pinia + Vite |
| 后端 | FastAPI + SQLModel + SQLite |
| AI | Anthropic SDK（跟 Workflow 一样的提示词流水线） |

## 快速开始（单端口）

只需启动一个后端服务，所有请求都走 `http://localhost:8000`。

```bash
# 1. 安装后端依赖
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入你的 ANTHROPIC_API_KEY

# 2. 构建前端（只需一次，有变更时重新构建）
cd ../frontend
npm install
npm run build

# 3. 启动服务（单端口，前端通过 FastAPI 静态文件 serve）
cd ../backend
python3 main.py
# → http://localhost:8000
```

打开浏览器访问 `http://localhost:8000`：
1. 在文本框中输入项目想法（10 个字符以上）
2. 点击「🚀 启动 Workflow」
3. 等待 Workflow 完成（约 2-5 分钟）
4. 浏览 PRD、架构设计、开发计划
5. 点击 Task 的「复制 Codex 指令」按钮，粘贴到 Codex 桌面版执行

### 开发模式（带热重载）

如果需要改前端并实时预览：

```bash
# 终端 1：后端
cd backend && python3 main.py

# 终端 2：前端开发服务器（自动代理 /api → 8000）
cd frontend && npm run dev
# → http://localhost:5173（热重载）
```

## 项目结构

```
claude-workflow-ui/
├── backend/
│   ├── main.py          # FastAPI 入口 + API 路由 + SSE + 静态文件 serve
│   ├── worker.py        # 3 步 Agent 流水线（PRD → 架构 → 任务）
│   ├── models.py        # SQLModel 数据模型
│   ├── schemas.py       # Pydantic 请求/响应模型
│   ├── config.py        # 环境变量配置
│   └── database.py      # SQLite 连接
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── NewProject.vue      # 表单页
│   │   │   └── ProjectResult.vue   # 结果展示页
│   │   ├── components/
│   │   │   ├── StatusTimeline.vue   # 进度时间线
│   │   │   ├── PrdViewer.vue        # PRD 渲染
│   │   │   ├── ArchitectureViewer.vue # 架构渲染
│   │   │   └── TaskListView.vue     # Task 清单 + 复制指令
│   │   ├── stores/project.ts       # Pinia 状态管理 + SSE
│   │   └── api/index.ts            # API 客户端
│   └── vite.config.ts              # 开发环境代理配置
└── README.md
```

## 与 Workflow 的关系

后端 `worker.py` 用 Anthropic SDK **重新实现了** `start-new-project` Workflow 的三步流水线，提示词完全一致。无需依赖 Claude Code CLI，通过 Web API 即可调用。

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/projects` | 创建项目并启动 Workflow |
| GET | `/api/projects` | 项目列表 |
| GET | `/api/projects/{id}` | 项目详情（含 Task） |
| GET | `/api/projects/{id}/stream` | SSE 实时进度 |
| GET | `/` | 前端页面（生产构建后） |
