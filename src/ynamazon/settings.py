from typing import override
import os
from pathlib import Path

from dotenv import dotenv_values
from pydantic import EmailStr, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .exceptions import MissingOpenAIAPIKey


class SecretApiKey(SecretStr):
    """Secret API key."""

    @override
    def _display(self) -> str:
        """Masked secret API key."""
        if self._secret_value is None:  # pyright: ignore[reportUnnecessaryComparison]
            return "****empty****"
        return self._secret_value[:4] + "****" + self._secret_value[-4:]


class SecretBudgetId(SecretStr):
    """Secret Budget ID."""

    @override
    def _display(self) -> str:
        """Masked secret Budget ID."""
        if self._secret_value is None:  # pyright: ignore[reportUnnecessaryComparison]
            return "****empty****"
        return self._secret_value[:4] + "****" + self._secret_value[-4:]


class Settings(BaseSettings):
    """Settings configuration for project."""

    model_config: SettingsConfigDict = SettingsConfigDict(  # pyright: ignore[reportIncompatibleVariableOverride]
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        extra="ignore",
    )

    ynab_api_key: SecretApiKey
    ynab_budget_id: SecretBudgetId
    amazon_user: EmailStr | None = None
    amazon_password: SecretStr | None = None
    openai_api_key: SecretApiKey | None = None

    ynab_payee_name_to_be_processed: str = "Amazon - Needs Memo"
    ynab_payee_name_processing_completed: str = "Amazon"
    ynab_use_markdown: bool = False
    use_ai_summarization: bool = False
    suppress_partial_order_warning: bool = False

    def get_amazon_accounts(self) -> list[tuple[str, EmailStr, SecretStr]]:
        """Get all configured Amazon accounts.

        Returns list of (account_name, email, password) tuples.

        Checks for numbered accounts (AMAZON_USER_1, AMAZON_PASSWORD_1, etc.).
        Falls back to legacy single account (AMAZON_USER, AMAZON_PASSWORD) if no numbered accounts found.
        """
        accounts: list[tuple[str, EmailStr, SecretStr]] = []

        # Load environment variables from .env file and OS environment
        env_file_path = Path(".env")
        env_vars = {}

        # First, load from .env file if it exists
        if env_file_path.exists():
            env_vars.update(dotenv_values(env_file_path))

        # Then override with actual OS environment variables
        env_vars.update(os.environ)

        # Check for numbered accounts (try both lowercase and uppercase)
        account_num = 1
        while True:
            # Try lowercase first (as used in .env files), then uppercase
            user_key_lower = f"amazon_user_{account_num}"
            password_key_lower = f"amazon_password_{account_num}"
            user_key_upper = f"AMAZON_USER_{account_num}"
            password_key_upper = f"AMAZON_PASSWORD_{account_num}"

            user = env_vars.get(user_key_lower) or env_vars.get(user_key_upper)
            password = env_vars.get(password_key_lower) or env_vars.get(password_key_upper)

            if user is None or password is None:
                break

            # Validate email format
            try:
                from pydantic.main import BaseModel

                class EmailValidator(BaseModel):
                    email: EmailStr

                validated = EmailValidator(email=user)
                accounts.append((f"Account {account_num}", validated.email, SecretStr(password)))
            except Exception:
                # Skip invalid email addresses
                pass

            account_num += 1

        # If no numbered accounts found, fall back to legacy single account
        if not accounts:
            if self.amazon_user is not None and self.amazon_password is not None:
                accounts.append(("Account 1", self.amazon_user, self.amazon_password))

        return accounts

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        """Validate settings constraints."""
        # Validate OpenAI API key when AI summarization is enabled
        if self.use_ai_summarization and self.openai_api_key is None:
            raise MissingOpenAIAPIKey("OpenAI API key is required when AI summarization is enabled")

        # Validate that at least one Amazon account is configured
        accounts = self.get_amazon_accounts()
        if not accounts:
            msg = (
                "No Amazon account configured. Please set either:\n"
                "  - Single account: AMAZON_USER and AMAZON_PASSWORD\n"
                "  - Multiple accounts: AMAZON_USER_1/AMAZON_PASSWORD_1, AMAZON_USER_2/AMAZON_PASSWORD_2, etc."
            )
            raise ValueError(msg)

        return self


settings = Settings()  # pyright: ignore[reportCallIssue]
