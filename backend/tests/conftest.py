import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("LLM_API_KEY", "test-key")


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    from app.config import get_settings

    get_settings.cache_clear()
