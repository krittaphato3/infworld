"""OpenAI-compatible LLM client singleton with retry logic."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import httpx
import openai

from config import settings


class LLMClient:
    """Thin wrapper around the OpenAI SDK for chat and image generation."""

    def __init__(self) -> None:
        self._chat_client = openai.AsyncOpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=httpx.Timeout(120.0),
        )
        self._image_client = openai.AsyncOpenAI(
            base_url=settings.image_api_url,
            api_key=settings.image_api_key,
            timeout=httpx.Timeout(120.0),
        )

    # ── Chat ──────────────────────────────────────────────────────────

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Send a chat completion request and return the assistant content."""
        response = await self._chat_client.chat.completions.create(
            model=model or settings.llm_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content: str | None = response.choices[0].message.content
        if content is None:
            raise RuntimeError("LLM returned an empty response (content is None)")
        return content.strip()

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        max_retries: int = 3,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Call chat() and parse the response as JSON with retry logic."""
        last_error: Exception | None = None
        for attempt in range(1, max_retries + 1):
            raw = await self.chat(messages, **kwargs)
            try:
                cleaned = self._strip_code_fences(raw)
                return json.loads(cleaned)
            except json.JSONDecodeError as exc:
                last_error = exc
                if attempt < max_retries:
                    await asyncio.sleep(1)
        raise RuntimeError(
            f"Failed to parse LLM response as JSON after {max_retries} attempts: "
            f"{last_error}"
        )

    # ── Image Generation ──────────────────────────────────────────────

    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
    ) -> str:
        """Generate an image and return a URL or base64 data URI."""
        response = await self._image_client.images.generate(
            model=settings.image_model,
            prompt=prompt,
            size=size,
            n=1,
        )
        image_data = response.data[0]
        if image_data.url:
            return image_data.url
        if image_data.b64_json:
            b64 = image_data.b64_json
            return f"data:image/png;base64,{b64}"
        raise RuntimeError("Image generation returned neither URL nor base64 data")

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove markdown code fences (```json ... ```) from LLM output."""
        pattern = r"^```(?:json)?\s*\n?(.*?)\n?\s*```$"
        match = re.match(pattern, text.strip(), re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()


llm_client = LLMClient()
