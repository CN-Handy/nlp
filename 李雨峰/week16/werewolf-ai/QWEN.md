# Werewolf AI — 狼人杀多智能体博弈系统

> 基于多 Agent 协作框架的狼人杀对战系统，AI 玩家通过 LLM 调用大模型进行推理、发言与决策。支持纯 AI 对战与人机混战（spectator 观战模式）。

## ⚠️ 安全禁忌

**API Key 绝对不能写入代码中（硬编码）。**
- LLM API Key 只能通过 `backend/.env` 文件配置（环境变量）
- `.env` 文件已在 `.gitignore` 中排除，不会被提交到 git
- 任何 `.py`、`.ts`、`.vue` 等源代码文件中不得出现真实 API Key

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Vue 3 + Vite + TypeScript + Element Plus + Pinia | 观战 UI，WebSocket 实时事件驱动 |
| 后端 | Python 3.10+ / FastAPI + uvicorn | REST API + WebSocket 服务 |
| AI Agent | Jinja2 prompt + LLM API (OpenAI 兼容格式) | 每个角色独立 Agent |
| 部署 | Docker Compose 或本地开发 | 前后端分离 |

## 项目结构

```
werewolf-ai/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── main.py           # 入口，CORS，路由挂载
│   │   ├── config.py         # pydantic-settings 配置（.env）
│   │   ├── api/              # REST 路由
│   │   │   ├── router.py     # /api/v1 聚合
│   │   │   ├── quick_start.py  # POST /quick/start 一键开局
│   │   │   ├── room.py       # 房间管理
│   │   │   └── game.py       # 游戏状态 + WS spectate 端点（含状态回放）
│   │   ├── core/             # 游戏引擎
│   │   │   ├── game_engine.py  # 状态机，驱动回合流转（speech callback）
│   │   │   ├── rules.py      # 角色能力、胜负判定、夜间结算
│   │   │   └── phases.py     # 阶段定义
│   │   ├── agents/           # AI Agent 实现
│   │   │   ├── base_agent.py   # 抽象基类 (decide, speak)
│   │   │   ├── werewolf.py     # 狼人 Agent
│   │   │   ├── seer.py         # 预言家 Agent
│   │   │   ├── witch.py        # 女巫 Agent
│   │   │   ├── hunter.py       # 猎人 Agent
│   │   │   ├── villager.py     # 村民 Agent
│   │   │   └── human_proxy.py  # 人类玩家代理
│   │   ├── llm/              # 大模型调用
│   │   │   ├── client.py       # 统一 LLM 调用接口
│   │   │   └── prompts/        # Jinja2 角色 prompt 模板
│   │   ├── services/         # 业务服务
│   │   │   ├── game_service.py # 游戏生命周期 + Agent 调度 + 事件日志
│   │   │   └── room_service.py # 房间管理
│   │   ├── ws/               # WebSocket
│   │   │   ├── manager.py      # 连接管理 + 广播
│   │   │   └── handlers.py     # 消息处理
│   │   ├── models/           # Pydantic 数据模型
│   │   │   └── game_state.py   # 含 event_log（事件回放）
│   │   └── utils/            # 工具函数
│   ├── requirements.txt
│   └── .env                  # 后端环境变量（LLM 配置，不提交到 git）
│
├── frontend/                 # Vue 3 前端
│   ├── src/
│   │   ├── api/http.ts       # Axios 封装 (baseURL: /api/v1)
│   │   ├── api/ws.ts         # WebSocket 服务 ({type,data} → {type,payload} 适配)
│   │   ├── views/
│   │   │   ├── HomeView.vue  # 首页，一键开局
│   │   │   └── GameView.vue  # 观战主界面（玩家卡片 + 事件流）
│   │   ├── stores/useGameStore.ts  # Pinia 状态
│   │   └── types/game.ts     # 类型定义
│   ├── vite.config.ts        # Vite 配置 (port 3000, /api → 8000, ws:true)
│   └── package.json
│
├── .gitignore                # 排除 .env、__pycache__、node_modules 等
├── docker-compose.yml        # Docker 部署
└── README.md                 # 项目说明
```

## 快速启动

### 后端

```bash
cd werewolf-ai/backend
pip install -r requirements.txt

# ⚠️ 编辑 .env 配置 LLM（不要提交到 git）
cp .env.example .env   # 如果 .env 不存在
# 编辑 .env 填入 LLM_API_KEY、LLM_BASE_URL 等

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端

```bash
cd werewolf-ai/frontend
npm install          # 如 node_modules 不存在
npm run dev          # http://localhost:3000
```

> 前端 Vite 开发服务器会将 `/api` 代理到 `http://localhost:8000`（含 WebSocket 升级，`ws: true`）。

### Docker Compose

```bash
cd werewolf-ai
docker compose up -d --build
```

## LLM 配置

在 `backend/.env` 中设置（pydantic-settings 从该目录读取）：

```env
LLM_PROVIDER=openai
LLM_API_KEY=<你的 API Key>       # ⚠️ 不要写死在代码中
LLM_BASE_URL=<API 地址>/v1       # OpenAI 兼容格式
LLM_MODEL=<模型名称>
```

| 变量 | 说明 |
|------|------|
| `LLM_PROVIDER` | `openai`（真实 API）或 `mock`（测试模式，随机行为） |
| `LLM_API_KEY` | API 密钥，仅存在于 `.env` 文件中 |
| `LLM_BASE_URL` | API 基础 URL，兼容 OpenAI 格式 |
| `LLM_MODEL` | 模型名称 |

## 核心架构

### 游戏引擎（状态机）

`GameEngine` 按狼人杀标准规则驱动回合：
- **夜晚阶段**：狼人刀人 → 预言家查验 → 女巫用药/毒
- **白天阶段**：死亡公布 → 顺序发言（通过 speech callback 调用 `agent.speak()` 获取真实发言）→ 投票放逐 → 结算
- 每阶段结束时通过 `broadcast_to_room` 推送 `GameEvent` 到 WebSocket

### 观战者事件回放

观战者连接时，`/api/v1/games/spectate/{room_id}` 端点会：
1. 发送当前玩家列表（含身份、死活，上帝视角）
2. 回放 `GameState.event_log` 中所有历史事件
3. 后续实时推送新事件

### 事件广播链

```
GameEngine 产生事件 → _on_game_event() 封装 payload
  → 记录到 game_state.event_log（回放用）
  → ws_manager.broadcast_to_room()
  → 所有玩家 + 观战者 WebSocket 接收
  → 前端 ws.ts 解析 {type, data} → {type, payload}
  → GameView.vue 更新玩家卡片 + 事件流
```

### 前端消息格式适配

后端发送 `{type: "game_event", data: {...}}`，前端 `ws.ts` 统一转换为 `{type, payload, timestamp}` 格式。`GameView.vue` 的 handler 接收解包后的 payload，从中提取 `event_type`、`data`、`actor_name`、`target_role` 等字段。

### 前端玩家状态可视化

`GameView.vue` 维护 `players` 响应式数组，通过事件驱动实时更新：
- `game_start`：初始化玩家列表（含 name、role=null、isAlive=true）
- `death`：更新目标玩家 `isAlive=false`，揭示 `role`
- `vote_result`：更新被淘汰玩家 `isAlive=false`，揭示 `role`
- `game_over`：揭示所有玩家身份和最终死活

## 关键 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/quick/start` | 一键开局（观战模式），创建 9 人 AI 对局 |
| WS | `/api/v1/games/spectate/{room_id}` | 观战 WebSocket 连接（含初始状态 + 事件回放） |
| GET | `/health` | 健康检查 |

## WebSocket 事件类型

| 事件 | 说明 |
|------|------|
| `game_start` | 游戏开始，携带完整玩家列表（id、name、role、is_alive） |
| `phase_change` | 阶段变更，含 from/to_phase |
| `speak` | 玩家发言，含 `text` 内容和发言者角色 |
| `death` | 玩家淘汰，含身份（target_role）和死因（killed_by） |
| `vote_result` | 投票结果，含得票明细（votes_received）和淘汰者 |
| `witch_poison` / `witch_heal` | 女巫用毒/救人 |
| `seer_inspect` | 预言家查验结果（is_werewolf） |
| `game_over` | 游戏结束，含获胜方和全部玩家身份揭示（all_roles） |
