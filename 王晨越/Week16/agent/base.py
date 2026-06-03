"""Agent 基类与大模型调用封装。"""

import json
import os
import random
import re
from abc import ABC, abstractmethod

from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """OpenAI 兼容 API；无 Key 时走 Mock 规则决策。"""

    def __init__(self) -> None:
        self.use_mock = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if self.api_key and os.getenv("USE_MOCK_LLM", "").lower() == "false":
            self.use_mock = False

    def chat(self, system: str, user: str, style: str = "balanced") -> str:
        if self.use_mock:
            return self._mock_response(user, style)
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=self._temperature(style),
                max_tokens=512,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            return self._mock_response(user, style, error=str(e))

    def _temperature(self, style: str) -> float:
        return {"cautious": 0.3, "bold": 0.9, "random": 1.0, "balanced": 0.6}.get(style, 0.6)

    def _mock_response(self, user: str, style: str, error: str = "") -> str:
        """规则化 Mock：从 prompt 中解析候选并返回 JSON"""
        if "发言" in user or "讨论" in user:
            speeches = [
                "我建议大家冷静分析昨晚的情况。",
                "我觉得有人发言前后矛盾，值得怀疑。",
                "目前信息不足，我先听听大家的意见。",
                "我怀疑玩家编号偏大的几位，理由是他们太安静了。",
            ]
            text = random.choice(speeches)
            return json.dumps({"speech": text}, ensure_ascii=False)

        # 投票 / 击杀 / 查验等：解析 alive 列表
        alive_match = re.search(r"存活玩家[：:]\s*\[([^\]]+)\]", user)
        candidates: list[int] = []
        if alive_match:
            candidates = [int(x.strip()) for x in alive_match.group(1).split(",") if x.strip().isdigit()]
        if not candidates:
            id_matches = re.findall(r"玩家(\d+)", user)
            candidates = list({int(x) for x in id_matches})[:6]

        if style == "cautious" and len(candidates) > 1:
            target = candidates[0]
        elif style == "bold" and candidates:
            target = candidates[-1]
        elif style == "random" and candidates:
            target = random.choice(candidates)
        else:
            target = random.choice(candidates) if candidates else 0

        if "投票" in user:
            return json.dumps({"vote": target}, ensure_ascii=False)
        if "查验" in user or "check" in user.lower():
            return json.dumps({"check": target}, ensure_ascii=False)
        if "击杀" in user or "kill" in user.lower():
            return json.dumps({"kill": target}, ensure_ascii=False)
        if "毒药" in user or "poison" in user.lower():
            use = random.choice([True, False])
            return json.dumps({"use_poison": use, "poison_target": target if use else None}, ensure_ascii=False)
        if "解药" in user or "save" in user.lower():
            use = random.choice([True, False])
            return json.dumps({"use_save": use}, ensure_ascii=False)
        if "开枪" in user:
            return json.dumps({"shoot": target}, ensure_ascii=False)
        if "总结" in user:
            return json.dumps(
                {"summary": "本局我过早暴露身份，下局应更谨慎发言并观察投票链。"},
                ensure_ascii=False,
            )
        return json.dumps({"target": target}, ensure_ascii=False)


class BaseAgent(ABC):
    """智能体抽象基类"""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    @abstractmethod
    def run(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        ...
