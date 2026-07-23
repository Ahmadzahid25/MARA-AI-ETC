"""Smoke tests for shared/config — proves the dev-environment TOML actually
loads and the two-database separation (ACCB Condition C-5) is real, not
just documented.
"""

from __future__ import annotations

import pytest

from shared.config.settings import Settings


@pytest.fixture(autouse=True)
def _dev_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('MARA_ENVIRONMENT', 'dev')


def test_dev_settings_load_from_configs_dev_toml() -> None:
    settings = Settings()
    assert settings.environment == 'dev'


def test_primary_and_dify_databases_are_distinct_instances() -> None:
    settings = Settings()
    # PostgresDsn with a "+driver" suffix (asyncpg here) resolves to pydantic's
    # MultiHostUrl, whose per-host info lives in .hosts() -> list[dict], not a
    # flat .host/.port pair — found by actually running this test, not by
    # inspection, which is exactly why this test exists.
    (primary_host_info,) = settings.database.primary_dsn.hosts()
    (dify_host_info,) = settings.database.dify_dsn.hosts()

    # Same host is fine (both point at localhost in dev); the databases and/or
    # ports must differ, otherwise this is the exact coupling ACCB Condition
    # C-5 exists to prevent (docs/architecture/09-knowledge-architecture.md §9.1.1).
    primary_key = (primary_host_info['host'], primary_host_info['port'])
    dify_key = (dify_host_info['host'], dify_host_info['port'])
    assert primary_key != dify_key
    assert settings.database.primary_dsn.path != settings.database.dify_dsn.path


def test_env_var_overrides_toml_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('MARA_ENVIRONMENT', 'dev')
    monkeypatch.setenv('MARA_AUTH__KEYCLOAK_REALM', 'overridden-realm')
    settings = Settings()
    assert settings.auth.keycloak_realm == 'overridden-realm'


def test_no_secret_default_reads_as_empty_or_placeholder() -> None:
    # configs/dev/settings.toml intentionally carries no secret fields (see
    # its own header comment) — this test documents that expectation so a
    # future PR adding a secret directly to a committed TOML file fails loudly.
    settings = Settings()
    assert settings.auth.keycloak_client_secret is None
