"""
Central settings loader.

Combines:
  - config/config.yaml   -> non-secret tunables, safe to commit
  - .env                 -> secrets and environment-specific values, NEVER committed

Usage:
    from config.settings import settings
    settings.llm_provider
    settings.cfg["detection"]["isolation_forest"]["n_estimators"]
"""
from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env", override=False)


class Settings:
    def __init__(self) -> None:
        self.root_dir = ROOT_DIR
        self.cfg = self._load_yaml(ROOT_DIR / "config" / "config.yaml")

        # LLM provider selection - provider-agnostic by design.
        self.llm_provider = os.getenv("LLM_PROVIDER", "mock").lower()
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        self.power_automate_webhook_url = os.getenv("POWER_AUTOMATE_WEBHOOK_URL", "")

        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("API_PORT", "8000"))

        self.vectorstore_dir = Path(
            os.getenv("VECTORSTORE_DIR", ROOT_DIR / self.cfg["rag"]["index_dir"])
        )

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        with open(path, "r") as f:
            return yaml.safe_load(f)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
