"""
SemanticMessageHistory Demo — redisvl
将多轮对话消息存入 Redis，并通过语义搜索检索与当前 prompt 最相关的历史消息，
比直接截取最近 N 条更节省 token 且上下文更精准。
"""

import os
from redisvl.extensions.message_history import SemanticMessageHistory
from redisvl.utils.vectorize import HFTextVectorizer

os.environ["TOKENIZERS_PARALLELISM"] = "false"

REDIS_URL = "redis://localhost:6379"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def build_history(session_tag: str = "demo-session") -> SemanticMessageHistory:
    return SemanticMessageHistory(
        name="chat_history",
        session_tag=session_tag,
        redis_url=REDIS_URL,
        distance_threshold=0.35,
        vectorizer=HFTextVectorizer(MODEL_NAME),
        overwrite=True,
    )


def populate_history(history: SemanticMessageHistory) -> None:
    """写入一段示例多轮对话。"""
    messages = [
        {"role": "user",      "content": "法国的首都是哪里？"},
        {"role": "assistant", "content": "法国的首都是巴黎。"},
        {"role": "user",      "content": "英国的人口大概是多少？"},
        {"role": "assistant", "content": "截至 2023 年，英国人口约 6700 万。"},
        {"role": "user",      "content": "Python 里怎么用列表推导式？"},
        {"role": "assistant", "content": "[expr for item in iterable if condition]"},
        {"role": "user",      "content": "Transformer 的注意力机制原理是什么？"},
        {"role": "assistant", "content": "注意力机制通过 Q/K/V 矩阵计算每个 token 对其他 token 的关注权重。"},
        {"role": "user",      "content": "德国和法国各有什么著名景点？"},
        {"role": "assistant", "content": "法国有埃菲尔铁塔、卢浮宫；德国有勃兰登堡门、新天鹅堡。"},
    ]
    history.add_messages(messages)
    print(f"[populate]  写入 {len(messages)} 条消息")


def demo_relevant(history: SemanticMessageHistory) -> None:
    """语义检索：找到与新 prompt 最相关的历史记录。"""
    queries = [
        "巴黎有什么值得去的地方？",           # 应命中"法国首都"和"著名景点"
        "请介绍一下英格兰的规模",              # 应命中"英国人口"
        "神经网络里的 attention 怎么算？",     # 应命中"Transformer"
    ]

    for q in queries:
        print(f"\n  Query: {q}")
        context = history.get_relevant(q, top_k=2)
        for msg in context:
            role = msg.get("role", "?")
            content = msg.get("content", "")
            print(f"    [{role}] {content[:60]}")


def demo_recent(history: SemanticMessageHistory) -> None:
    """时序检索：按时间顺序取最近 N 条。"""
    recent = history.get_recent(top_k=4)
    print(f"\n[get_recent top_k=4]  共 {len(recent)} 条")
    for msg in recent:
        print(f"  [{msg['role']}] {msg['content'][:50]}")


def demo_store_and_drop(history: SemanticMessageHistory) -> None:
    """演示 store 写入 prompt‑response 对，以及 drop 删除单条。"""
    history.store(
        prompt="欧洲最小的国家是哪个？",
        response="摩纳哥是欧洲面积最小的国家。",
    )
    print("\n[store]  新增一条 Q/A 对")

    # 检索刚写入的内容
    hits = history.get_relevant("欧洲最小的国家", top_k=1)
    if hits:
        print(f"[relevant]  命中: {hits[0]['content'][:60]}")

    # 删除刚写入的最新一条（raw=True 返回 entry_id）
    latest_raw = history.get_recent(top_k=1, raw=True)
    if latest_raw:
        entry_id = latest_raw[0]["entry_id"]
        history.drop(entry_id)
        print(f"[drop]  已删除 entry_id={entry_id[:20]}...")


def demo_multi_session() -> None:
    """演示多 session 隔离：不同 session_tag 的消息互不干扰。"""
    for user in ("alice", "bob"):
        h = SemanticMessageHistory(
            name="chat_history",
            session_tag=user,
            redis_url=REDIS_URL,
            vectorizer=HFTextVectorizer(MODEL_NAME),
            overwrite=False,
        )
        h.add_message(
            {"role": "user", "content": f"你好，我是 {user}，请记住我的名字。"},
            session_tag=user,
        )

    for user in ("alice", "bob"):
        h = SemanticMessageHistory(
            name="chat_history",
            session_tag=user,
            redis_url=REDIS_URL,
            vectorizer=HFTextVectorizer(MODEL_NAME),
            overwrite=False,
        )
        msgs = h.get_recent(top_k=1, session_tag=user)
        if msgs:
            print(f"  [{user}]  {msgs[0]['content']}")


def simulate_llm_chat(history: SemanticMessageHistory, user_input: str) -> str:
    """模拟带记忆的对话：用语义历史作为上下文。"""
    context_msgs = history.get_relevant(user_input, top_k=3)
    # 实际场景中将 context_msgs + user_input 拼给 LLM
    history.add_message({"role": "user", "content": user_input})
    response = f"[模拟回复] 根据 {len(context_msgs)} 条历史记录，回答「{user_input[:20]}...」"
    history.add_message({"role": "assistant", "content": response})
    return response


def main() -> None:
    print("=" * 55)
    print("  SemanticMessageHistory Demo")
    print("=" * 55)

    history = build_history()
    populate_history(history)

    print("\n── 语义检索 ──────────────────────────────────────────")
    demo_relevant(history)

    print("\n── 时序检索 ──────────────────────────────────────────")
    demo_recent(history)

    print("\n── store / drop ──────────────────────────────────────")
    demo_store_and_drop(history)

    print("\n── 多 session 隔离 ───────────────────────────────────")
    demo_multi_session()

    print("\n── 模拟带记忆的对话 ──────────────────────────────────")
    resp = simulate_llm_chat(history, "法国有什么旅游胜地？")
    print(f"  {resp}")

    history.clear()
    print("\n[clear]  history cleared.")


if __name__ == "__main__":
    main()
