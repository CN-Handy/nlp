"""
SemanticCache Demo — redisvl
对 LLM 回复做语义级缓存：相似度足够高的 prompt 直接返回缓存结果，
无需再次调用 LLM，节省 API 费用并降低延迟。
"""

import os
import time
from redisvl.extensions.cache.llm import SemanticCache
from redisvl.utils.vectorize import HFTextVectorizer
from redisvl.query.filter import Tag

os.environ["TOKENIZERS_PARALLELISM"] = "false"

REDIS_URL = "redis://localhost:6379"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def build_cache(distance_threshold: float = 0.15) -> SemanticCache:
    """distance_threshold 越小，匹配越严格（余弦距离范围 0‑2）。"""
    return SemanticCache(
        name="llmcache",
        redis_url=REDIS_URL,
        distance_threshold=distance_threshold,
        vectorizer=HFTextVectorizer(MODEL_NAME),
        ttl=600,
    )


def simulate_llm(prompt: str) -> str:
    """模拟 LLM 推理（实际使用时替换为真实 API 调用）。"""
    answers = {
        "法国的首都是哪里": "法国的首都是巴黎。",
        "自然语言处理": "自然语言处理（NLP）是 AI 的重要分支，研究计算机如何理解和生成人类语言。",
    }
    for key, val in answers.items():
        if key in prompt:
            return val
    return f"[模拟回复] 关于「{prompt[:30]}」的答案。"


def ask_with_cache(cache: SemanticCache, prompt: str) -> str:
    """先查缓存，命中则直接返回；否则调用 LLM 并写入缓存。"""
    hits = cache.check(prompt=prompt, num_results=1)
    if hits:
        print(f"  [CACHE HIT]  distance={hits[0]['vector_distance']:.4f}")
        return hits[0]["response"]

    print("  [CACHE MISS]  calling LLM...")
    t0 = time.time()
    response = simulate_llm(prompt)
    elapsed = time.time() - t0

    cache.store(
        prompt=prompt,
        response=response,
        metadata={"model": "simulated", "latency_ms": round(elapsed * 1000, 1)},
    )
    return response


def demo_basic(cache: SemanticCache) -> None:
    """演示基础存取与语义命中。"""
    pairs = [
        ("法国的首都是哪里？", None),
        ("法国首都叫什么名字？", None),       # 语义相似 → 应命中
        ("Paris 是哪个国家的首都？", None),   # 语义较远 → 可能未命中
    ]

    for prompt, _ in pairs:
        print(f"\nQ: {prompt}")
        ans = ask_with_cache(cache, prompt)
        print(f"A: {ans}")


def demo_threshold(cache: SemanticCache) -> None:
    """演示动态调整 distance_threshold 的效果。"""
    base_prompt = "NLP 是什么？"
    similar_prompt = "自然语言处理是什么？"

    cache.store(prompt=base_prompt, response=simulate_llm(base_prompt))

    print(f"\n── threshold=0.15（严格）")
    cache.set_threshold(0.15)
    hits = cache.check(prompt=similar_prompt)
    print(f"  '{similar_prompt}' 命中: {bool(hits)}")

    print(f"\n── threshold=0.5（宽松）")
    cache.set_threshold(0.5)
    hits = cache.check(prompt=similar_prompt)
    if hits:
        print(f"  '{similar_prompt}' 命中, distance={hits[0]['vector_distance']:.4f}")
        print(f"  cached response: {hits[0]['response']}")


def demo_filter(cache_no_filter: SemanticCache) -> None:
    """演示带 Tag 过滤器的用户隔离缓存。"""
    private_cache = SemanticCache(
        name="private_llmcache",
        redis_url=REDIS_URL,
        distance_threshold=0.2,
        vectorizer=HFTextVectorizer(MODEL_NAME),
        filterable_fields=[{"name": "user_id", "type": "tag"}],
        overwrite=True,
    )

    private_cache.store(
        prompt="我的订单状态如何？",
        response="您的订单 #1001 正在配送中。",
        filters={"user_id": "alice"},
    )
    private_cache.store(
        prompt="我的订单状态如何？",
        response="您的订单 #2002 已完成配送。",
        filters={"user_id": "bob"},
    )

    for user in ("alice", "bob", "carol"):
        f = Tag("user_id") == user
        hits = private_cache.check(prompt="我的订单状态如何？", filter_expression=f)
        if hits:
            print(f"  user={user}: {hits[0]['response']}")
        else:
            print(f"  user={user}: 无缓存记录")

    private_cache.delete()


def main() -> None:
    print("=" * 55)
    print("  SemanticCache Demo")
    print("=" * 55)

    cache = build_cache()
    cache.clear()

    print("\n── 基础语义缓存 ──────────────────────────────────────")
    demo_basic(cache)

    print("\n── 动态阈值调整 ──────────────────────────────────────")
    demo_threshold(cache)

    print("\n── 用户级隔离过滤 ────────────────────────────────────")
    demo_filter(cache)

    cache.delete()
    print("\n[done]  cache deleted.")


if __name__ == "__main__":
    main()
