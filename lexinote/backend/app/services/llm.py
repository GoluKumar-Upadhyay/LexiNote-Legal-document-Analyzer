from __future__ import annotations

import time
from typing import Any

import requests

from app.core.config import settings

try:
    import vertexai
    from langchain_google_vertexai import ChatVertexAI
except Exception:  # pragma: no cover
    vertexai = None
    ChatVertexAI = None


class UnifiedLLM:
    def __init__(self) -> None:
        self._vertex_client = None
        self._vertex_error: str | None = None
        self._provider_cooldowns: dict[str, float] = {}

    def available_providers(self) -> dict[str, bool]:
        return {
            "gemini": self._gemini_ready(),
            "xai": bool(settings.xai_api_key) and self._provider_ready("xai"),
            "openrouter": bool(settings.openrouter_api_key) and self._provider_ready("openrouter"),
            "groq": bool(settings.groq_api_key) and self._provider_ready("groq"),
            "heuristic": True,
        }

    def _provider_ready(self, provider: str) -> bool:
        return time.time() >= self._provider_cooldowns.get(provider, 0)

    def _set_provider_cooldown(self, provider: str, seconds: int) -> None:
        self._provider_cooldowns[provider] = time.time() + seconds

    def _cooldown_for_exception(self, exc: Exception) -> int:
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            if exc.response.status_code in {401, 403}:
                return 900
            if exc.response.status_code == 429:
                return 300
        if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
            return 180
        return 0

    def _gemini_ready(self) -> bool:
        if settings.gemini_api_key:
            return True
        return bool(ChatVertexAI and vertexai and settings.project_id and settings.prepare_google_credentials())

    def _get_vertex_client(self) -> Any:
        if self._vertex_client is not None:
            return self._vertex_client
        if self._vertex_error is not None:
            raise RuntimeError(self._vertex_error)
        if not (ChatVertexAI and vertexai and settings.project_id and settings.prepare_google_credentials()):
            self._vertex_error = "Vertex Gemini is not configured."
            raise RuntimeError(self._vertex_error)

        vertexai.init(project=settings.project_id, location=settings.vertex_location)
        self._vertex_client = ChatVertexAI(
            model=settings.gemini_model,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_output_tokens,
            project=settings.project_id,
        )
        return self._vertex_client

    def _call_gemini_api(
        self,
        prompt: str,
        system_message: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout_seconds: int = 40,
    ) -> str:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": f"{system_message}\n\n{prompt}"}]}],
                "generationConfig": {
                    "temperature": settings.llm_temperature if temperature is None else temperature,
                    "maxOutputTokens": settings.llm_max_output_tokens if max_tokens is None else max_tokens,
                },
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError("Gemini returned no candidates.")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "\n".join(part.get("text", "") for part in parts if part.get("text"))
        if not text:
            raise RuntimeError("Gemini returned empty text.")
        return text

    def _call_openai_compatible(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        prompt: str,
        system_message: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout_seconds: int = 30,
        extra_headers: dict[str, str] | None = None,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "temperature": settings.llm_temperature if temperature is None else temperature,
                "max_tokens": settings.llm_max_output_tokens if max_tokens is None else max_tokens,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("Provider returned no choices.")
        content = choices[0].get("message", {}).get("content", "")
        if not content:
            raise RuntimeError("Provider returned empty content.")
        return str(content)

    def generate(
        self,
        prompt: str,
        system_message: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> tuple[str, str]:
        errors: list[str] = []
        for provider in settings.llm_provider_priority:
            if provider in {"xai", "openrouter", "groq"} and not self._provider_ready(provider):
                continue
            try:
                if provider == "gemini":
                    if settings.gemini_api_key:
                        return self._call_gemini_api(
                            prompt,
                            system_message,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            timeout_seconds=40,
                        ), "gemini_api"
                    client = self._get_vertex_client()
                    content = client.invoke(f"{system_message}\n\n{prompt}").content
                    return str(content), "gemini_vertex"

                if provider == "xai" and settings.xai_api_key:
                    return (
                        self._call_openai_compatible(
                            base_url="https://api.x.ai/v1",
                            api_key=settings.xai_api_key,
                            model=settings.xai_model,
                            prompt=prompt,
                            system_message=system_message,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            timeout_seconds=12,
                        ),
                        "xai",
                    )

                if provider == "openrouter" and settings.openrouter_api_key:
                    return (
                        self._call_openai_compatible(
                            base_url="https://openrouter.ai/api/v1",
                            api_key=settings.openrouter_api_key,
                            model=settings.openrouter_model,
                            prompt=prompt,
                            system_message=system_message,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            timeout_seconds=35,
                            extra_headers={
                                "HTTP-Referer": settings.openrouter_site_url,
                                "X-Title": settings.openrouter_app_name,
                            },
                        ),
                        "openrouter",
                    )

                if provider == "groq" and settings.groq_api_key:
                    return (
                        self._call_openai_compatible(
                            base_url="https://api.groq.com/openai/v1",
                            api_key=settings.groq_api_key,
                            model=settings.groq_model,
                            prompt=prompt,
                            system_message=system_message,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            timeout_seconds=20,
                        ),
                        "groq",
                    )
            except Exception as exc:
                cooldown = self._cooldown_for_exception(exc)
                if cooldown and provider in {"xai", "openrouter", "groq"}:
                    self._set_provider_cooldown(provider, cooldown)
                errors.append(f"{provider}: {exc}")

        raise RuntimeError("; ".join(errors) or "No provider available.")


llm = UnifiedLLM()
