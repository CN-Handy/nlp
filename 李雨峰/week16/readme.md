狼人杀多智能体博弈系统 — 技术架构与工程目录
一、项目概述
本项目实现一个基于多 Agent 协作框架的狼人杀对战系统，支持纯 AI 对战与人机混战。每个玩家（Agent）根据角色拥有独立目标、信息视野与行动空间，在严格信息隔离下通过调用远程大模型进行推理、发言与决策。系统需提供完整对局引擎、回合流转、胜负裁决及结构化日志；前端提供观战 UI，实时展示多智能体博弈过程。

二、技术栈
层级	技术选型	说明
前端框架	Vite + Vue 3 + TypeScript	响应式 UI，快速开发
状态管理	Pinia	管理前端全局状态（房间、对局信息）
实时通信	WebSocket (Socket.IO / 原生)	双向推送对局事件与玩家行动
UI 组件	Naive UI 或 Element Plus	快速搭建观战界面
后端框架	Python 3.10+ / FastAPI	提供 REST API 与 WebSocket 支持
游戏引擎	自研状态机 (Python)	驱动夜间/昼间阶段、胜负判定
大模型调用	httpx / aiohttp + 远程 API	调用 OpenAI/Claude/本地模型等
数据校验	Pydantic v2	定义请求/响应、游戏事件模型
日志存储	JSONL 文件 + 结构化日志 (structlog)	全程可观测，便于复盘
房间管理	内存 + SQLite（可选）	管理多局并发房间
部署	Docker + docker-compose	前后端一体化部署
三、系统架构
text
┌─────────────────────┐      WebSocket       ┌────────────────────────────┐
│  Frontend (Vue)      │◄────────────────────►│  Backend (FastAPI)         │
│  - GameLobby         │                      │  - API Router             │
│  - SpectateView      │                      │  - WebSocket Manager      │
│  - PlayerActionBar   │                      │  - GameRoom Service       │
│  - Chat/History      │                      │  - Game Engine            │
│  - PlayerList        │                      │  - Agent Dispatcher       │
│                      │                      │  - LLM Client             │
└─────────────────────┘                      └────────────────────────────┘
核心模块交互流程
用户/客户端 通过 REST 创建房间或加入房间（人机混战指定人类玩家座位）。

房间管理服务 初始化 GameEngine，分配角色（狼人、预言家、女巫、村民等），为每个座位创建 Agent 实例（人类座位则创建 HumanProxyAgent）。

WebSocket 通道 将前端与该房间绑定，随后所有阶段转换、发言、投票、行动结果均以 JSON 事件推送。

GameEngine 按狼人杀标准规则驱动回合：

夜晚阶段：狼人刀人 → 预言家查验 → 女巫用药/毒 → 猎人/白痴等技能触发。

昼间阶段：公布死亡信息 → 顺序发言 → 投票放逐 → 遗言/技能结算。

胜负判定：狼人存活数 vs 神职/村民存活数。

每个 AI Agent 在需要决策时，由 Agent Dispatcher 调用 LLM Client，向远程大模型发送包含角色提示、历史对话、当前信息（仅限该角色可见）的 prompt，解析返回的结构化动作（JSON）。

人类玩家通过 PlayerActionBar 提交行动，经由 WebSocket 返回后端，引擎统一处理。

所有对局事件、玩家发言、决策原因等均由 结构化日志 记录，并可通过 API 查询或回放。

四、目录结构
text
werewolf-ai/
├── frontend/                          # 前端项目
│   ├── public/
│   ├── src/
│   │   ├── assets/                    # 静态资源
│   │   ├── components/                # 公共组件
│   │   │   ├── PlayerCard.vue
│   │   │   ├── ChatBox.vue
│   │   │   ├── VotePanel.vue
│   │   │   ├── PhaseBanner.vue
│   │   │   └── ActionSelector.vue     # 人类玩家操作界面
│   │   ├── views/                     # 页面
│   │   │   ├── HomeView.vue           # 首页/创建房间
│   │   │   ├── LobbyView.vue          # 房间等待
│   │   │   └── GameView.vue           # 对局主界面（观战/参战）
│   │   ├── stores/                    # Pinia 状态
│   │   │   ├── useRoomStore.ts
│   │   │   └── useGameStore.ts
│   │   ├── api/                       # HTTP + WebSocket 封装
│   │   │   ├── http.ts
│   │   │   └── ws.ts
│   │   ├── types/                     # 类型定义
│   │   │   └── game.ts
│   │   ├── router/
│   │   ├── App.vue
│   │   └── main.ts
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── backend/                           # 后端项目
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI 启动入口
│   │   ├── config.py                  # 配置管理（环境变量/文件）
│   │   ├── api/                       # 接口层
│   │   │   ├── __init__.py
│   │   │   ├── router.py              # 路由汇总
│   │   │   ├── room.py               # 房间创建/加入/设置
│   │   │   └── game.py               # 对局相关接口（开始、查询历史）
│   │   ├── ws/                        # WebSocket 管理
│   │   │   ├── __init__.py
│   │   │   ├── manager.py            # 连接管理、事件广播
│   │   │   └── handlers.py           # 客户端消息处理
│   │   ├── core/                      # 游戏引擎
│   │   │   ├── __init__.py
│   │   │   ├── game_engine.py         # 核心状态机（回合流转）
│   │   │   ├── rules.py               # 角色技能、胜负判定
│   │   │   ├── phases.py              # 夜晚/昼间各阶段定义
│   │   │   └── events.py             # 对局事件定义（死亡、发言等）
│   │   ├── agents/                    # 智能体定义
│   │   │   ├── __init__.py
│   │   │   ├── base_agent.py          # Agent 抽象基类
│   │   │   ├── werewolf.py
│   │   │   ├── villager.py
│   │   │   ├── seer.py
│   │   │   ├── witch.py
│   │   │   ├── hunter.py
│   │   │   └── human_proxy.py         # 人类玩家代理（转接前端输入）
│   │   ├── llm/                       # 大模型调用
│   │   │   ├── __init__.py
│   │   │   ├── client.py              # 统一 LLM 调用接口（支持多模型）
│   │   │   └── prompts/               # 各角色 System Prompt 模板
│   │   │       ├── werewolf.j2
│   │   │       ├── seer.j2
│   │   │       └── ...
│   │   ├── services/                  # 业务服务
│   │   │   ├── __init__.py
│   │   │   ├── room_service.py        # 房间生命周期管理
│   │   │   └── game_service.py        # 对局启动、调度
│   │   ├── models/                    # Pydantic 数据模型
│   │   │   ├── __init__.py
│   │   │   ├── room.py
│   │   │   ├── game_state.py
│   │   │   ├── messages.py            # Agent 输入输出模型
│   │   │   └── events.py
│   │   ├── utils/                     # 工具函数
│   │   │   ├── logger.py              # 结构化日志配置
│   │   │   ├── id_gen.py
│   │   │   └── serialization.py
│   │   └── data/                      # 运行时数据存储
│   │       ├── rooms.json             # 房间状态持久化（可选）
│   │       └── logs/                  # 对局日志存储目录
│   │           └── game_<id>.jsonl
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── Dockerfile
│
├── docker-compose.yml                 # 一体化部署配置
└── README.md
五、关键技术设计
1. 信息隔离机制
每个 Agent 实例维护独立的 View，只包含：

自身身份与技能状态

夜间行动结果（仅自己可见的信息，如预言家查验结果、狼人同伴）

公共聊天历史（发言、死亡公告）
决策 prompt 仅注入 View 中的信息，确保信息不对称。

2. Agent 决策协议
所有 AI Agent 的决策统一通过以下 JSON 格式与大模型交互：

json
{
  "action": "vote" | "kill" | "check" | "save" | "poison" | "speak" | "pass",
  "target": "player_id",  // 可选
  "message": "发言内容"   // 用于 speak 动作
}
后端解析并校验合法性后执行。

3. 对局事件流
游戏引擎将所有事件（阶段开始、玩家行动、死亡、投票、游戏结束）包装为 GameEvent，通过 WebSocket 推送：

json
{
  "event_type": "PHASE_CHANGE",
  "phase": "NIGHT",
  "round": 2,
  "data": { ... }
}
前端根据事件类型增量更新 UI，保证所有客户端状态一致。

4. 结构化日志
每局游戏生成一个 .jsonl 文件，每行记录一个带时间戳的事件或决策，包含：

完整游戏上下文（角色分配、座位）

每轮每位玩家的推理过程（可选，通过 prompt 要求 LLM 输出推理）

最终胜负与关键转折点
该日志可直接用于复盘、评测指标计算。

5. 人类玩家接入
HumanProxyAgent 继承 BaseAgent，但不调用 LLM。其 decide() 方法将决策请求通过 WebSocket 发送给前端，前端弹出对应操作界面（如夜晚狼人杀人选择器、白天发言输入框），用户提交后结果返回后端继续流程。后端设置超时机制，超时则随机行动或弃权。

六、进阶拓展预留
评测+复盘：日志模块已记录结构化数据，可外接评测服务计算胜率、投票准确率、谎言识别率等指标，并提供复盘回放。

自进化 Agent：可在 agents 模块中加入经验记忆与反思机制，将历史对局日志作为 Few-shot 示例或微调数据，实现“对局→分析→优化→再对局”闭环。

通用 Agent 演化：Agent 基类设计为可插拔，支持从通用聊天 Agent 渐进加载角色设定与规则知识，实现“读懂自己→修改自己→运行自己”。