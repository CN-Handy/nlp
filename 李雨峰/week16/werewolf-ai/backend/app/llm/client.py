"""Unified LLM client supporting OpenAI, Claude, and mock providers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import httpx
import structlog
from jinja2 import Environment, FileSystemLoader

from app.config import settings
from app.models.messages import AgentAction, AgentActionType

logger = structlog.get_logger()

# Jinja2 environment for prompt templates
_template_dir = Path(__file__).resolve().parent / "prompts"
_jinja_env = Environment(loader=FileSystemLoader(str(_template_dir)), trim_blocks=True, lstrip_blocks=True)


def render_prompt(template_name: str, **kwargs: Any) -> str:
    """Render a prompt template with the given variables."""
    template = _jinja_env.get_template(f"{template_name}.j2")
    return template.render(**kwargs)


class LLMClient:
    """
    Unified LLM client that supports OpenAI, Claude, and mock providers.

    Usage:
        client = LLMClient()
        result = await client.generate_action(...)
    """

    def __init__(self):
        self.provider = settings.llm_provider
        self.model = settings.llm_model
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url or "https://api.openai.com/v1"

        # Claude-specific
        self.claude_api_key = settings.claude_api_key
        self.claude_model = settings.claude_model

    async def generate_action(
        self,
        role: str,
        game_state_info: dict[str, Any],
        phase: str,
        context: Optional[dict[str, Any]] = None,
    ) -> AgentAction:
        """
        Generate an AgentAction from the LLM based on role and game context.

        In mock mode, returns a random valid action.
        """
        if settings.is_mock_mode:
            return await self._mock_action(role, game_state_info, phase)

        prompt = render_prompt(
            role,
            game_state=game_state_info,
            phase=phase,
            context=context or {},
        )

        try:
            if self.provider == "openai":
                return await self._call_openai(prompt, role)
            elif self.provider == "claude":
                return await self._call_claude(prompt, role)
            else:
                return await self._mock_action(role, game_state_info, phase)
        except Exception as e:
            logger.error("LLM call failed, falling back to mock", error=str(e), provider=self.provider)
            return await self._mock_action(role, game_state_info, phase)

    async def generate_speech(
        self,
        role: str,
        game_state_info: dict[str, Any],
        discussion_history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate a speech message for the discussion phase."""
        if settings.is_mock_mode:
            return await self._mock_speech(role, game_state_info)

        prompt = render_prompt(
            role,
            game_state=game_state_info,
            phase="discussion",
            context={"discussion_history": discussion_history or []},
        )

        try:
            if self.provider == "openai":
                return await self._call_openai_for_text(prompt)
            elif self.provider == "claude":
                return await self._call_claude_for_text(prompt)
            else:
                return await self._mock_speech(role, game_state_info)
        except Exception as e:
            logger.error("Speech generation failed", error=str(e))
            return "I have nothing to add right now."

    # --- OpenAI ---

    async def _call_openai(self, prompt: str, role: str) -> AgentAction:
        """Call OpenAI API for structured action output."""
        system_prompt = self._get_system_prompt(role)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return self._parse_action_json(content)

    async def _call_openai_for_text(self, prompt: str) -> str:
        """Call OpenAI API for free-form text (speech)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

    # --- Claude ---

    async def _call_claude(self, prompt: str, role: str) -> AgentAction:
        """Call Claude API for structured action output."""
        system_prompt = self._get_system_prompt(role)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.claude_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.claude_model,
                    "max_tokens": 1024,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["content"][0]["text"]
            return self._parse_action_json(content)

    async def _call_claude_for_text(self, prompt: str) -> str:
        """Call Claude API for free-form text."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.claude_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.claude_model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"].strip()

    # --- Mock ---

    async def _mock_action(self, role: str, game_state_info: dict[str, Any], phase: str) -> AgentAction:
        """Return a mock action for testing."""
        import random

        valid_targets = game_state_info.get("valid_targets", [])
        target = random.choice(valid_targets) if valid_targets else None

        action_map: dict[str, AgentActionType] = {
            "werewolf": AgentActionType.KILL,
            "seer": AgentActionType.INSPECT,
            "witch": AgentActionType.SAVE,
            "villager": AgentActionType.VOTE,
            "hunter": AgentActionType.VOTE,
        }

        action_type = action_map.get(role, AgentActionType.SKIP)

        return AgentAction(
            action_type=action_type,
            target_id=target,
            reasoning=f"[MOCK] {role} decided to {action_type.value} target {target} in phase {phase}",
            confidence=0.7,
        )

    async def _mock_speech(self, role: str, game_state_info: dict[str, Any]) -> str:
        """Return mock speech for testing."""
        speeches = [
            "I think we should be careful about who we vote for.",
            "Based on what I've heard, I suspect someone is hiding their role.",
            "I'm a simple villager trying to find the truth here.",
            "Let's analyze the facts and vote wisely today.",
            "I don't have much information yet, but I'm watching closely.",
        ]
        import random
        return f"[MOCK {role}] {random.choice(speeches)}"

    # --- Helpers ---

    def _get_system_prompt(self, role: str) -> str:
        """Get system prompt for the given role."""
        role_system_prompts = {
            "werewolf": (
                "You are playing a werewolf role in Werewolf (Mafia) game. "
                "You must respond with a JSON object containing your action. "
                "Format: {\"action_type\": \"kill\", \"target_id\": \"player_xxx\", \"reasoning\": \"...\"}"
            ),
            "seer": (
                "You are playing a seer role in Werewolf game. "
                "You can inspect one player to learn if they are a werewolf. "
                "Respond with JSON: {\"action_type\": \"inspect\", \"target_id\": \"player_xxx\", \"reasoning\": \"...\"}"
            ),
            "witch": (
                "You are playing a witch role. You can save someone from werewolf kill or poison a player. "
                "Respond with JSON: {\"action_type\": \"save\"|\"poison\", \"target_id\": \"player_xxx\", \"reasoning\": \"...\"}"
            ),
            "villager": (
                "You are a villager in Werewolf game. Vote to eliminate a suspected werewolf. "
                "Respond with JSON: {\"action_type\": \"vote\", \"target_id\": \"player_xxx\", \"reasoning\": \"...\"}"
            ),
            "hunter": (
                "You are a hunter in Werewolf game. Vote to eliminate a suspected werewolf. "
                "If you die, you can shoot one player. "
                "Respond with JSON: {\"action_type\": \"vote\", \"target_id\": \"player_xxx\", \"reasoning\": \"...\"}"
            ),
        }
        return role_system_prompts.get(role, "You are playing Werewolf game. Respond with a JSON action.")

    def _parse_action_json(self, content: str) -> AgentAction:
        """Parse JSON content into AgentAction."""
        try:
            # Try to find JSON in the response
            content = content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)
            action_type_str = data.get("action_type", "skip")
            action_type = AgentActionType(action_type_str) if action_type_str in [e.value for e in AgentActionType] else AgentActionType.SKIP

            return AgentAction(
                action_type=action_type,
                target_id=data.get("target_id"),
                reasoning=data.get("reasoning", ""),
                confidence=data.get("confidence", 0.5),
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning("Failed to parse LLM action JSON", error=str(e), content=content[:100])
            return AgentAction(
                action_type=AgentActionType.SKIP,
                reasoning=f"Failed to parse LLM response: {e}",
            )


# Module-level singleton
llm_client = LLMClient()
