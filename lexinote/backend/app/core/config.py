from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def _csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass
class Settings:
    app_name: str = os.getenv("APP_NAME", "LexiNote API")
    app_env: str = os.getenv("APP_ENV", "development")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", "26214400"))
    allow_origins: list[str] = None  # type: ignore[assignment]
    llm_provider_priority: list[str] = None  # type: ignore[assignment]
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    llm_max_output_tokens: int = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "24576"))
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    project_id: str = os.getenv("PROJECT_ID", "").strip()
    vertex_location: str = os.getenv("VERTEX_LOCATION", "us-central1")
    vertex_ai_key: str = os.getenv("VERTEX_AI_KEY", "").strip()
    google_application_credentials: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    xai_api_key: str = os.getenv("XAI_API_KEY", "").strip()
    xai_model: str = os.getenv("XAI_MODEL", "grok-4.3")
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "").strip()
    openrouter_model: str = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    openrouter_site_url: str = os.getenv("OPENROUTER_SITE_URL", "http://localhost")
    openrouter_app_name: str = os.getenv("OPENROUTER_APP_NAME", "LexiNote")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "").strip()
    groq_model: str = os.getenv("GROQ_MODEL", "qwen/qwen3-32b")
    video_width: int = int(os.getenv("VIDEO_WIDTH", "1280"))
    video_height: int = int(os.getenv("VIDEO_HEIGHT", "720"))
    video_slide_seconds: float = float(os.getenv("VIDEO_SLIDE_SECONDS", "3.5"))

    def __post_init__(self) -> None:
        if self.allow_origins is None:
            self.allow_origins = _csv_env(
                "ALLOW_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            )
        if self.llm_provider_priority is None:
            self.llm_provider_priority = _csv_env(
                "LLM_PROVIDER_PRIORITY",
                "gemini,xai,openrouter,groq,heuristic",
            )

    def prepare_google_credentials(self) -> str | None:
        if self.google_application_credentials and Path(self.google_application_credentials).exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.google_application_credentials
            return self.google_application_credentials

        if not self.vertex_ai_key:
            return None

        if self.vertex_ai_key.startswith("{"):
            handle = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
            handle.write(self.vertex_ai_key.encode("utf-8"))
            handle.flush()
            handle.close()
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = handle.name
            return handle.name

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.vertex_ai_key
        return self.vertex_ai_key


settings = Settings()
