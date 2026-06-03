# AI 狼人杀 Agent Team

## 目录结构

```
agent/          # 智能体：基类、玩家 Agent、总结 Agent
engine/         # 对局引擎（主持人逻辑、回合流转）
roles/          # 角色定义：目标、行动空间、信息可见性
schema/         # Pydantic 数据模型（对话、对局记录）
memory/         # 跨局经验存储与检索
game_logging/   # 结构化对局日志（避免与 stdlib logging 冲突）
api/            # FastAPI 观战/控制接口
frontend/       # Vue 观战 UI
tests/          # 单元测试
configs/        # 对局配置（人数、角色配比）
logs/           # 运行日志输出目录
```

## 开发约定

- 角色逻辑与 Agent 决策分离：`roles/` 管规则，`agent/` 管 LLM 调用
- 信息隔离：夜间行动、查验结果等通过 `visible_to` 过滤后传给 Agent
- 所有对外事件使用中文阶段名（如「夜晚-狼人」「白天-发言」）
- 玩家显示名：`玩家{N}（{角色中文名}）`
