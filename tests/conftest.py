"""Test configuration and fixtures."""

import os
from typing import Any

import pytest

# Set environment variables BEFORE any imports that might use settings
# This needs to happen at module import time, before pytest collects tests
test_env_vars = {
    "YNAB_API_KEY": "test_ynab_api_key_1234567890",
    "YNAB_BUDGET_ID": "test_budget_id_1234567890",
    "AMAZON_USER": "test@example.com",
    "AMAZON_PASSWORD": "test_password_1234567890",
    "YNAB_PAYEE_NAME_TO_BE_PROCESSED": "Amazon - Needs Memo",
    "YNAB_PAYEE_NAME_PROCESSING_COMPLETED": "Amazon",
    "YNAB_USE_MARKDOWN": "false",
    "USE_AI_SUMMARIZATION": "false",
    "SUPPRESS_PARTIAL_ORDER_WARNING": "false",
}

for key, value in test_env_vars.items():
    os.environ.setdefault(key, value)


@pytest.fixture(autouse=True)
def reset_settings_cache(monkeypatch: Any) -> None:
    """Reset the settings singleton before each test.

    This ensures each test gets a fresh settings instance
    and can override environment variables as needed.
    """
    # Clear the cached settings module to force reload
    import sys

    if "ynamazon.settings" in sys.modules:
        del sys.modules["ynamazon.settings"]
