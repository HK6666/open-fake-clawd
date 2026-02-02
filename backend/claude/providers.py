"""LLM Provider abstraction for multiple backends."""

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Optional, Dict, Any

import httpx
import jwt

from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM provider."""
    content: str
    model: str
    usage: Dict[str, int] = None
    cost: float = 0.0
    raw: Dict[str, Any] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        system: str = None,
        stream: bool = False
    ) -> AsyncIterator[str]:
        """Send chat messages and get streaming response."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic API provider."""

    def __init__(self):
        self.api_key = settings.anthropic_api_key
        self.model = settings.anthropic_model
        self.base_url = "https://api.anthropic.com/v1"

    def get_name(self) -> str:
        return f"Anthropic ({self.model})"

    async def chat(
        self,
        messages: list[dict],
        system: str = None,
        stream: bool = False
    ) -> AsyncIterator[str]:
        """Chat with streaming response."""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
            "stream": True
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=settings.claude_timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/messages",
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                        except json.JSONDecodeError:
                            pass


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(self):
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.base_url = "https://api.openai.com/v1"

    def get_name(self) -> str:
        return f"OpenAI ({self.model})"

    async def chat(
        self,
        messages: list[dict],
        system: str = None,
        stream: bool = False
    ) -> AsyncIterator[str]:
        """Chat with streaming response."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # OpenAI uses system message in messages array
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": all_messages,
            "stream": True
        }

        async with httpx.AsyncClient(timeout=settings.claude_timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            data = json.loads(line[6:])
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            pass


class OpenRouterProvider(LLMProvider):
    """OpenRouter API provider (supports many models)."""

    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.model = settings.openrouter_model
        self.base_url = "https://openrouter.ai/api/v1"

    def get_name(self) -> str:
        return f"OpenRouter ({self.model})"

    async def chat(
        self,
        messages: list[dict],
        system: str = None,
        stream: bool = False
    ) -> AsyncIterator[str]:
        """Chat with streaming response."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ccbot",
            "X-Title": "ccBot"
        }

        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": all_messages,
            "stream": True
        }

        async with httpx.AsyncClient(timeout=settings.claude_timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            data = json.loads(line[6:])
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            pass


class GLMProvider(LLMProvider):
    """GLM (智谱AI) API provider."""

    def __init__(self):
        self.api_key = settings.glm_api_key
        self.model = settings.glm_model
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"
        # Try JWT auth if API key has format {id}.{secret}, otherwise use direct auth
        self.use_jwt = "." in self.api_key

    def get_name(self) -> str:
        return f"GLM ({self.model})"

    def _generate_token(self, exp_seconds: int = 3600) -> str:
        """
        Generate JWT token from API key.

        GLM API key format: {id}.{secret}
        Token expires after exp_seconds (default: 1 hour)
        """
        try:
            api_key_id, secret = self.api_key.split(".")
        except ValueError:
            raise ValueError(
                "Invalid GLM API key format. Expected format: {id}.{secret}\n"
                "Get your API key from: https://bigmodel.cn/usercenter/proj-mgmt/apikeys"
            )

        payload = {
            "api_key": api_key_id,
            "exp": int(round(time.time() * 1000)) + exp_seconds * 1000,
            "timestamp": int(round(time.time() * 1000)),
        }

        return jwt.encode(
            payload,
            secret,
            algorithm="HS256",
            headers={"alg": "HS256", "sign_type": "SIGN"},
        )

    async def chat(
        self,
        messages: list[dict],
        system: str = None,
        stream: bool = False
    ) -> AsyncIterator[str]:
        """Chat with streaming response."""
        # Choose authentication method
        if self.use_jwt:
            # Generate JWT token from {id}.{secret} format API key
            token = self._generate_token()
            logger.debug("Using JWT authentication for GLM API")
        else:
            # Use API key directly
            token = self.api_key
            logger.debug("Using direct API key authentication for GLM API")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": all_messages,
            "stream": True
        }

        logger.debug(f"GLM API Request: model={self.model}, messages_count={len(all_messages)}, use_jwt={self.use_jwt}")

        async with httpx.AsyncClient(timeout=settings.claude_timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    logger.error(f"GLM API Error: status={response.status_code}, body={error_body.decode()}")
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            data = json.loads(line[6:])
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            pass


def get_llm_provider() -> Optional[LLMProvider]:
    """
    Get the configured LLM provider.

    Returns None if using claude-cli (handled separately).
    """
    provider = settings.llm_provider.lower()

    if provider == "claude-cli":
        return None  # Use ClaudeRunner instead

    elif provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        return AnthropicProvider()

    elif provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        return OpenAIProvider()

    elif provider == "openrouter":
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY not configured")
        return OpenRouterProvider()

    elif provider == "glm":
        if not settings.glm_api_key:
            raise ValueError("GLM_API_KEY not configured")
        return GLMProvider()

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
