"""Typed configuration loading for MARA AI-ETC.

Implements docs/architecture/03-repository-structure.md's `shared/config` module:
environment resolution + typed config, layered as

    environment variables  (highest precedence — secrets, deploy-time overrides)
    configs/<env>/*.toml   (environment-specific, non-secret config)
    field defaults         (lowest precedence)

No secret value is ever read from a TOML file under configs/ — those are committed
to the repository and are non-secret by construction (docs/architecture/
13-deployment-architecture.md §13.1). Secrets come from the environment (which, in
production, is populated by Vault/K8s Secrets per docs/architecture/
11-security-architecture.md §11.3), never from a config file.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = REPO_ROOT / 'configs'

Environment = Literal['dev', 'staging', 'production']


class DatabaseSettings(BaseSettings):
    """Two separate database instances by design — see docs/architecture/
    09-knowledge-architecture.md §9.1.1 (ACCB Condition C-5): the platform's
    primary Postgres (conversations/tasks/shared/audit memory, workflow
    checkpoints) must never be the same instance as Dify's own operational
    database.
    """

    primary_dsn: PostgresDsn = Field(
        default='postgresql+asyncpg://mara:mara@localhost:5432/mara_platform',
        description='Primary Postgres: memory, audit, workflow checkpoints, pgvector.',
    )
    dify_dsn: PostgresDsn = Field(
        default='postgresql+asyncpg://dify:dify@localhost:5433/dify',
        description="Dify's own operational database — a separate instance, "
        'never shared',
    )


class ObjectStorageSettings(BaseSettings):
    endpoint_url: str = Field(default='http://localhost:9000')
    access_key: SecretStr = Field(default=SecretStr('mara-dev'))
    secret_key: SecretStr = Field(default=SecretStr('mara-dev-secret'))
    bucket: str = Field(default='mara-documents')
    secure: bool = Field(default=False, description='TLS. Must be true outside dev.')


class RedisSettings(BaseSettings):
    dsn: RedisDsn = Field(default='redis://localhost:6379/0')


class AuthSettings(BaseSettings):
    """Keycloak federation — docs/architecture/04-technology-stack.md §4.4,
    wired through openhands/app_server/user_auth per docs/repo-audit/
    06-openhands-protection-rules.md §6.2 (extend, don't fork).
    """

    keycloak_server_url: str = Field(default='http://localhost:8080')
    keycloak_realm: str = Field(default='mara-ai-etc')
    keycloak_client_id: str = Field(default='mara-officer-workspace')
    keycloak_client_secret: SecretStr | None = Field(default=None)
    mfa_required: bool = Field(
        default=True,
        description='Non-negotiable for any role with approval authority — '
        'docs/architecture/11-security-architecture.md §11.2.',
    )


class ObservabilitySettings(BaseSettings):
    otel_exporter_endpoint: str | None = Field(default='http://localhost:4317')
    langfuse_public_key: SecretStr | None = Field(default=None)
    langfuse_secret_key: SecretStr | None = Field(default=None)
    langfuse_host: str = Field(default='http://localhost:3300')


class Settings(BaseSettings):
    """Root settings object. One instance per process, resolved once via
    ``get_settings()`` and passed down explicitly — never re-read ad hoc,
    so a single request/workflow run sees a consistent configuration snapshot.
    """

    model_config = SettingsConfigDict(
        env_prefix='MARA_',
        env_nested_delimiter='__',
        extra='ignore',
    )

    environment: Environment = Field(default='dev')

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    object_storage: ObjectStorageSettings = Field(default_factory=ObjectStorageSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    gateway_correlation_header: str = Field(default='X-MARA-Correlation-Id')

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Precedence, highest first: init kwargs > env vars > configs/<env>/*.toml
        # > defaults. This is what makes environment variables able to override a
        # committed configs/<env>/settings.toml value at deploy time without
        # editing the repo.
        toml_source = TomlConfigSettingsSource(
            settings_cls,
            toml_file=_config_file_for_environment(),
        )
        return (init_settings, env_settings, toml_source, file_secret_settings)


def _config_file_for_environment() -> Path:
    import os

    env = os.environ.get('MARA_ENVIRONMENT', 'dev')
    path = CONFIGS_DIR / env / 'settings.toml'
    return path if path.exists() else CONFIGS_DIR / 'dev' / 'settings.toml'


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide cached settings singleton.

    Cached deliberately: re-resolving settings mid-process (mid-workflow, in
    particular) could let a config change silently alter behavior partway
    through an in-flight, checkpointed workflow instance — see docs/
    architecture/07-workflow-architecture.md on checkpoint consistency.
    """

    return Settings()
