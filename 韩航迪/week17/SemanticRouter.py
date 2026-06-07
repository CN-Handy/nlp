"""
SemanticRouter Demo — redisvl
根据用户输入的语义，将请求路由到最匹配的处理分支，
比关键词匹配更鲁棒，比完整 LLM 分类更快更省钱。
"""

import os
from redisvl.extensions.router import SemanticRouter, Route
from redisvl.extensions.router.schema import RoutingConfig, DistanceAggregationMethod
from redisvl.utils.vectorize import HFTextVectorizer

os.environ["TOKENIZERS_PARALLELISM"] = "false"

REDIS_URL = "redis://localhost:6379"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


# ── 1. 定义路由 ────────────────────────────────────────────────────────────────

def build_routes() -> list[Route]:
    """每条 Route 由若干参考句子描述该路由的语义范围。"""
    return [
        Route(
            name="greeting",
            references=[
                "你好",
                "嗨，你好呀",
                "早上好",
                "Hi there!",
                "Hello, how are you?",
            ],
            metadata={"category": "social", "handler": "greeting_handler"},
            distance_threshold=0.55,
        ),
        Route(
            name="technology",
            references=[
                "AI 最新进展是什么？",
                "深度学习有什么新突破？",
                "推荐一款好用的编程工具",
                "什么是大语言模型？",
                "GPT 和 BERT 有什么区别？",
            ],
            metadata={"category": "tech", "handler": "tech_handler"},
            distance_threshold=0.60,
        ),
        Route(
            name="customer_support",
            references=[
                "我的订单在哪里？",
                "如何退货退款？",
                "我想投诉",
                "账单有问题",
                "产品质量太差了",
            ],
            metadata={"category": "support", "handler": "support_handler"},
            distance_threshold=0.55,
        ),
        Route(
            name="farewell",
            references=[
                "再见",
                "拜拜",
                "下次见",
                "Goodbye!",
                "See you later",
            ],
            metadata={"category": "social", "handler": "farewell_handler"},
            distance_threshold=0.55,
        ),
    ]


# ── 2. 模拟各路由处理函数 ──────────────────────────────────────────────────────

HANDLERS = {
    "greeting":         lambda q: f"[问候处理] 你好！有什么可以帮您？",
    "technology":       lambda q: f"[技术处理] 关于「{q[:20]}」，让我查阅技术文档...",
    "customer_support": lambda q: f"[客服处理] 已收到您的问题「{q[:20]}」，转接人工客服...",
    "farewell":         lambda q: f"[告别处理] 感谢使用，再见！",
    None:               lambda q: f"[默认处理] 未能识别意图，请换一种说法。",
}


# ── 3. Demo 函数 ───────────────────────────────────────────────────────────────

def demo_single_route(router: SemanticRouter) -> None:
    """单路由匹配：返回距离最近的一条路由。"""
    queries = [
        "嗨，你好啊",
        "怎么实现 Transformer 的自注意力？",
        "我上周买的东西还没收到",
        "好的，今天就聊到这里吧",
        "今天天气真不错",          # 可能 no match
    ]

    print(f"\n{'Query':<30}  {'Route':<20}  {'Distance':<10}  Response")
    print("-" * 85)
    for q in queries:
        match = router(q)
        name = match.name if match else None
        dist = f"{match.distance:.4f}" if match else "—"
        response = HANDLERS[name](q)
        print(f"{q:<30}  {str(name):<20}  {dist:<10}  {response}")


def demo_multi_route(router: SemanticRouter) -> None:
    """多路由匹配：返回 top-k 条匹配，用于混合意图场景。"""
    query = "AI 技术可以帮我解决售后问题吗？"
    matches = router.route_many(query, max_k=3, distance_threshold=0.7)
    print(f"\n  Query: {query}")
    if matches:
        for m in matches:
            print(f"    route={m.name:<20}  distance={m.distance:.4f}")
    else:
        print("    未找到匹配路由")


def demo_dynamic_management(router: SemanticRouter) -> None:
    """演示动态添加 / 查询 / 删除参考句。"""
    # 添加新参考
    new_keys = router.add_route_references(
        route_name="technology",
        references=["大模型微调怎么做？", "RAG 检索增强生成是什么？"],
    )
    print(f"\n[add_refs]  新增 {len(new_keys)} 条参考")

    # 验证添加效果
    match = router("RAG 有哪些应用场景？")
    print(f"[verify]    route={match.name if match else None}, dist={match.distance:.4f if match else '—'}")

    # 查询现有参考
    refs = router.get_route_references(route_name="technology")
    print(f"[get_refs]  technology 共 {len(refs)} 条参考")

    # 删除刚才添加的参考
    deleted = router.delete_route_references(keys=new_keys)
    print(f"[del_refs]  已删除 {deleted} 条")


def demo_routing_config(routes: list[Route]) -> None:
    """演示 RoutingConfig — 调整聚合方式和全局阈值。"""
    config = RoutingConfig(
        max_k=2,
        aggregation_method=DistanceAggregationMethod.min,  # 取最近参考的距离
    )
    router2 = SemanticRouter(
        name="config-router",
        routes=routes,
        vectorizer=HFTextVectorizer(MODEL_NAME),
        routing_config=config,
        redis_url=REDIS_URL,
        overwrite=True,
    )
    match = router2("你好呀，最近有什么 AI 新消息？")
    print(f"\n[routing_config]  min-agg  route={match.name if match else None}")
    router2.delete()


def demo_serialization(router: SemanticRouter) -> None:
    """演示序列化：to_dict / from_dict 和 to_yaml / from_yaml。"""
    # dict 序列化
    d = router.to_dict()
    print(f"\n[to_dict]   routes={[r['name'] for r in d['routes']]}")

    restored = SemanticRouter.from_dict(
        d,
        vectorizer=HFTextVectorizer(MODEL_NAME),
        redis_url=REDIS_URL,
        overwrite=True,
    )
    match = restored("订单没收到怎么办？")
    print(f"[from_dict] route={match.name if match else None}")

    # YAML 序列化
    yaml_path = "router_config.yaml"
    router.to_yaml(yaml_path, overwrite=True)
    print(f"[to_yaml]   saved to {yaml_path}")

    router_yaml = SemanticRouter.from_yaml(
        yaml_path,
        vectorizer=HFTextVectorizer(MODEL_NAME),
        redis_url=REDIS_URL,
        overwrite=True,
    )
    match2 = router_yaml("再见了")
    print(f"[from_yaml] route={match2.name if match2 else None}")

    restored.delete()
    router_yaml.delete()


# ── 4. 入口 ────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 55)
    print("  SemanticRouter Demo")
    print("=" * 55)

    routes = build_routes()
    router = SemanticRouter(
        name="demo-router",
        routes=routes,
        vectorizer=HFTextVectorizer(MODEL_NAME),
        routing_config=RoutingConfig(
            max_k=1,
            aggregation_method=DistanceAggregationMethod.avg,
        ),
        redis_url=REDIS_URL,
        overwrite=True,
    )

    print("\n── 单路由匹配 ────────────────────────────────────────")
    demo_single_route(router)

    print("\n── 多路由匹配（混合意图）────────────────────────────")
    demo_multi_route(router)

    print("\n── 动态管理参考句 ────────────────────────────────────")
    demo_dynamic_management(router)

    print("\n── RoutingConfig 配置 ────────────────────────────────")
    demo_routing_config(routes)

    print("\n── 序列化 / 反序列化 ─────────────────────────────────")
    demo_serialization(router)

    router.delete()
    print("\n[done]  router deleted.")


if __name__ == "__main__":
    main()
