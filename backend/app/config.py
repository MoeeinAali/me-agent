"""Runtime configuration, read from the environment (and `.env` in development)."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# The hrcando career-page web app ships this key to every visitor's browser; it is not a secret.
# Kept overridable so a rotation on their side needs only an env change.
_HRCANDO_PUBLIC_CAREER_AUTH_KEY = (
    "QEBtH9TdWnvuVYAAkBfSuBKzix0ppSq5lPoQN5TzifR31fs9HxPZYpm5Mdk0TyV4d8KQ3ueaxV1mZjlwE0jrdvmNwwDgUnaVl"
    "JCc3Eaon2Ac9LwEzDVCX5fjrJn9WmU5"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str

    llm_base_url: str = "https://api.gapgpt.app/v1"
    llm_api_key: SecretStr
    llm_model_understand: str = "gpt-4.1-mini"
    llm_model_generate: str = "gpt-4.1"
    llm_model_embed: str = "text-embedding-3-small"
    llm_model_stt: str = "whisper-1"
    llm_model_tts: str = "gpt-4o-mini-tts"
    llm_model_judge: str = "gemini-2.5-flash"
    llm_timeout_seconds: float = 60.0
    embed_dim: int = 1536

    data_dir: Path = Path("../data")

    github_token: SecretStr | None = None
    hrcando_career_auth_key: str = _HRCANDO_PUBLIC_CAREER_AUTH_KEY

    cors_origins: list[str] = ["http://localhost:3000"]
    rate_limit: str = "30/minute"
    # Behind a CDN or ingress every visitor arrives from a handful of proxy IPs. Name the header
    # the proxy puts the visitor's IP in (Cloudflare: cf-connecting-ip, ingress-nginx: x-real-ip)
    # to rate-limit per visitor. It is honoured only from the proxies listed here (CIDRs), so a
    # client that bypasses the proxy can't set it.
    rate_limit_client_header: str | None = None
    rate_limit_trusted_proxies: list[str] = []

    max_message_chars: int = 2000
    max_job_chars: int = 20_000
    max_pdf_bytes: int = 2_000_000
    max_audio_bytes: int = 10_000_000
    max_audio_seconds: int = 60

    @field_validator("hrcando_career_auth_key", mode="before")
    @classmethod
    def _keep_public_key_when_blank(cls, value: object) -> object:
        """A blank HRCANDO_CAREER_AUTH_KEY= line in .env must not wipe the built-in key."""
        return value or _HRCANDO_PUBLIC_CAREER_AUTH_KEY

    @property
    def record_path(self) -> Path:
        return self.data_dir / "record.json"

    @property
    def syllabus_path(self) -> Path:
        return self.data_dir / "syllabus.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
