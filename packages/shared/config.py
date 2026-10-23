"""Application settings loaded from environment / .env."""
from __future__ import annotations

from pathlib import Path
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+psycopg://stockpred:stockpred@localhost:5432/stockpred"
    )
    newsapi_key: str = Field(default="")
    watchlist_raw: str = Field(default="AAPL,MSFT,NVDA", alias="WATCHLIST")
    log_level: str = Field(default="INFO")

    alpaca_key_id: str = Field(default="", alias="ALPACA_KEY_ID")
    alpaca_secret_key: str = Field(default="", alias="ALPACA_SECRET_KEY")
    alpaca_base_url: str = Field(
        default="https://paper-api.alpaca.markets", alias="ALPACA_BASE_URL"
    )
    risk_halt: bool = Field(default=False, alias="RISK_HALT")
    max_prediction_age_days: int = Field(default=3, alias="MAX_PREDICTION_AGE_DAYS")
    max_prediction_trading_days: int = Field(default=1, alias="MAX_PREDICTION_TRADING_DAYS")

    api_host: str = Field(default="127.0.0.1", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    clerk_publishable_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "CLERK_PUBLISHABLE_KEY", "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY"
        ),
    )
    clerk_jwks_url: str = Field(default="", alias="CLERK_JWKS_URL")
    clerk_issuer: str = Field(default="", alias="CLERK_ISSUER")
    clerk_audience: str = Field(default="", alias="CLERK_AUDIENCE")
    clerk_pem_public_key: str = Field(default="", alias="CLERK_PEM_PUBLIC_KEY")

    model_config = SettingsConfigDict(
        env_file=(
            PROJECT_ROOT / ".env",
            PROJECT_ROOT / "apps" / "dashboard" / ".env.local",
        ),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def watchlist(self) -> list[str]:
        return [s.strip().upper() for s in self.watchlist_raw.split(",") if s.strip()]

    @property
    def watchlist_alpaca_eligible(self) -> list[str]:
        """Return watchlist symbols that Alpaca paper trading can route (US equities only).

        Excluded suffixes:
          .NS  — NSE-listed Indian equities
          -USD — Crypto pairs (BTC-USD, ETH-USD, …)
          =F   — Commodity futures (GC=F, CL=F, …)
        """
        _excluded_suffixes = (".NS", "-USD", "=F")
        return [s for s in self.watchlist if not any(s.endswith(e) for e in _excluded_suffixes)]

    @property
    def resolved_clerk_jwks_url(self) -> str:
        if self.clerk_jwks_url:
            return self.clerk_jwks_url
        domain = self._clerk_frontend_domain
        if domain:
            return f"https://{domain}/.well-known/jwks.json"
        return ""

    @property
    def resolved_clerk_issuer(self) -> str:
        if self.clerk_issuer:
            return self.clerk_issuer
        domain = self._clerk_frontend_domain
        if domain:
            return f"https://{domain}"
        return ""

    @property
    def _clerk_frontend_domain(self) -> str:
        pub = self.clerk_publishable_key
        if not pub:
            import os
            pub = os.environ.get("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "")
        if not pub:
            return ""
        parts = pub.split("_")
        if len(parts) >= 3:
            import base64
            padded = parts[2] + "=" * ((4 - len(parts[2]) % 4) % 4)
            try:
                return base64.b64decode(padded).decode("utf-8", errors="ignore").rstrip("$")
            except Exception:
                return ""
        return ""


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings  # pylint: disable=global-statement
    if _settings is None:
        _settings = Settings()
    return _settings
