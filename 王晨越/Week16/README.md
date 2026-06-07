# AI 狼人杀 — 多智能体 Agent Team

基于多 Agent 协作的狼人杀系统：每个角色拥有独立目标与信息视野，由 LLM（或 Mock 规则）驱动发言与决策；对局引擎负责回合流转与胜负裁决，并输出结构化 JSON 日志。

## 功能概览

| 模块 | 说明 |
|------|------|
| `roles/` | 角色基类 + 狼人/预言家/女巫/猎人/村民 |
| `agent/` | 玩家 Agent、总结 Agent、LLM 封装 |
| `engine/` | 对局引擎（夜晚/白天/投票/猎人） |
| `schema/` | Pydantic 对话与对局记录 |
| `memory/` | 跨局经验 JSON 持久化 |
| `api/` | FastAPI 创建/步进/跑完/查询 |
| `frontend/` | Vue 观战页（CDN 单页） |

## 快速开始

### 1. 安装依赖

```bash
cd 新建文件夹
pip install -r requirements-install.txt
```

### 2. 环境变量（可选）

复制 `.env.example` 为 `.env`：

- **Mock 模式（默认）**：`USE_MOCK_LLM=true`，无需 API Key，适合本地演示与测试。
- **真实 LLM**：设置 `OPENAI_API_KEY`，并设 `USE_MOCK_LLM=false`（支持 OpenAI 兼容接口）。

### 3. 命令行演示

```bash
python main_demo.py
python main_demo.py --config standard_6
python main_demo.py --manual   # 手动按 Enter 推每一步
```

日志保存在 `logs/<game_id>.json`。

### 4. 启动 API

```bash
uvicorn api.server:app --reload --host 127.0.0.1 --port 8000
```

接口文档：http://127.0.0.1:8000/docs

主要接口：

- `POST /games` — 创建对局
- `POST /games/{id}/step` — 推进一步（一夜+一日）
- `POST /games/{id}/run` — 自动跑完并保存
- `GET /games/{id}` — 状态与对话
- `GET /experiences/{role}` — 角色历史经验

### 5. 前端观战

先启动 API，再用浏览器打开：

```bash
# 方式一：直接打开文件
start frontend/index.html

# 方式二：本地静态服务
python -m http.server 5173 --directory frontend
# 访问 http://127.0.0.1:5173
```

在页面中：新建对局 → 推进一步 / 一键跑完 → 查看日志与赛后总结。

### 6. 测试

```bash
pytest tests/ -v
```

## 项目结构

```
agent/           # 智能体
engine/          # 对局引擎
roles/           # 角色定义
schema/          # 数据模型
memory/          # 经验库
game_logging/    # 日志持久化
configs/         # 对局配置
api/             # FastAPI
frontend/        # Vue 观战 UI
tests/           # 单元测试
main_demo.py     # 最小演示入口
logs/            # 运行输出（自动创建）
```

## 对照作业要求

- **多 Agent 协作/对抗**：每角色独立 `PlayerAgent`，狼人夜间信息仅队友可见（`visible_to`）。
- **信息隔离**：查验、用药、狼刀等通过 `DialogueRecord.visible_to` 过滤。
- **对局引擎**：`GameEngine` 驱动回合与胜负。
- **结构化日志**：`GameRecord` + `logs/*.json`。
- **加分：观战 UI**：`frontend/index.html` + FastAPI。
- **进阶（自进化雏形）**：`SummaryAgent` + `memory/experience.py` 沉淀复盘供下局 prompt 使用。

## 参考开发顺序

详见案例文件 `狼人杀.claude.txt`（从 `/init` 建目录 → roles → engine → demo → API → 前端 → 总结与经验）。
