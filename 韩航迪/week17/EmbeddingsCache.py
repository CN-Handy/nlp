"""
EmbeddingsCache Demo — redisvl
将文本 embedding 结果缓存到 Redis，避免重复调用 Embedding API。
"""

import os
from redisvl.extensions.cache.embeddings import EmbeddingsCache
from redisvl.utils.vectorize import HFTextVectorizer

os.environ["TOKENIZERS_PARALLELISM"] = "false"

REDIS_URL = "redis://localhost:6379"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def build_cache() -> EmbeddingsCache:
    return EmbeddingsCache(
        name="embedcache",
        redis_url=REDIS_URL,
        ttl=3600,  # 缓存 1 小时后自动过期
    )


def demo_single_ops(cache: EmbeddingsCache, vectorizer: HFTextVectorizer) -> None:
    """演示单条 set / get / exists / drop。"""
    text = "什么是机器学习？"
    embedding = vectorizer.embed(text)

    # ── 写入 ──────────────────────────────────────────────
    key = cache.set(
        content=text,
        model_name=MODEL_NAME,
        embedding=embedding,
        metadata={"category": "AI", "lang": "zh"},
    )
    print(f"[set]  key={key}")

    # ── 读取 ──────────────────────────────────────────────
    result = cache.get(content=text, model_name=MODEL_NAME)
    if result:
        print(f"[get]  content={result['content']}")
        print(f"       embedding 维度={len(result['embedding'])}")
        print(f"       metadata={result.get('metadata', {})}")

    # ── 判断是否存在 ──────────────────────────────────────
    exists = cache.exists(content=text, model_name=MODEL_NAME)
    print(f"[exists] {exists}")

    # ── 删除 ──────────────────────────────────────────────
    cache.drop(content=text, model_name=MODEL_NAME)
    print(f"[drop]  deleted, exists now: {cache.exists(text, MODEL_NAME)}")


def demo_batch_ops(cache: EmbeddingsCache, vectorizer: HFTextVectorizer) -> None:
    """演示批量 mset / mget。"""
    texts = [
        "深度学习是什么？",
        "自然语言处理的主要任务有哪些？",
        "Transformer 模型的核心思想是什么？",
    ]
    embeddings = vectorizer.embed_many(texts)

    # ── 批量写入 ──────────────────────────────────────────
    batch_items = [
        {
            "content": texts[i],
            "model_name": MODEL_NAME,
            "embedding": embeddings[i],
            "metadata": {"idx": i},
        }
        for i in range(len(texts))
    ]
    keys = cache.mset(batch_items)
    print(f"\n[mset]  stored {len(keys)} embeddings")

    # ── 批量读取 ──────────────────────────────────────────
    results = cache.mget(contents=texts, model_name=MODEL_NAME)
    for text, res in zip(texts, results):
        hit = "HIT" if res else "MISS"
        print(f"[mget]  {hit}  |  {text[:20]}...")


def demo_vectorizer_with_cache() -> None:
    """将 EmbeddingsCache 挂载到 HFTextVectorizer，embed 时自动读写缓存。"""
    cache = EmbeddingsCache(name="vect_cache", redis_url=REDIS_URL, ttl=600)

    # 先不挂载缓存，正常 embed
    vect_no_cache = HFTextVectorizer(model=MODEL_NAME)

    text = "Redis 向量库有什么优势？"
    emb1 = vect_no_cache.embed(text)

    # 手动写入缓存
    cache.set(content=text, model_name=MODEL_NAME, embedding=emb1)

    # 下次 get 直接命中
    cached = cache.get(content=text, model_name=MODEL_NAME)
    print(f"\n[vectorizer+cache]  缓存命中: {cached is not None}")
    print(f"  embedding shape: {len(cached['embedding'])}")

    cache.drop(content=text, model_name=MODEL_NAME)


def main() -> None:
    print("=" * 55)
    print("  EmbeddingsCache Demo")
    print("=" * 55)

    vectorizer = HFTextVectorizer(model=MODEL_NAME)
    cache = build_cache()

    print("\n── 单条操作 ──────────────────────────────────────────")
    demo_single_ops(cache, vectorizer)

    print("\n── 批量操作 ──────────────────────────────────────────")
    demo_batch_ops(cache, vectorizer)

    print("\n── Vectorizer + Cache ────────────────────────────────")
    demo_vectorizer_with_cache()

    # 清理
    cache.clear()
    print("\n[clear]  cache cleared.")


if __name__ == "__main__":
    main()
