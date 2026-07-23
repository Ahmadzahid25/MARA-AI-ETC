"""Unit tests for services/api_gateway/auth.py - Keycloak JWT/JWKS validation.

Tests cover the Principal dataclass, _JwksCache TTL caching,
get_current_principal() FastAPI dependency, and require_role() factory.

Includes both happy-path and rejected-token scenarios per the Milestone 0
requirement: at least one test for a rejected/invalid token.

NOTE on key material: These tests use authlib for both JWT signing and
verification to ensure key format compatibility.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from authlib.jose import JsonWebKey, JsonWebToken
from fastapi import HTTPException

from services.api_gateway.auth import (
    Principal,
    _JwksCache,
    get_current_principal,
    require_role,
)
from shared.config.settings import Settings


@pytest.fixture(autouse=True)
def _dev_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('MARA_ENVIRONMENT', 'dev')


@pytest.fixture
def test_settings() -> Settings:
    return Settings()


@pytest.fixture
def rsa_jwk() -> dict:
    """Generate a fresh RSA key pair as a JWK, exported with its private
    component (as_dict() defaults to public-only regardless of the
    is_private flag passed to generate_key())."""
    return JsonWebKey.generate_key('RSA', 2048, is_private=True).as_dict(
        is_private=True
    )


@pytest.fixture
def valid_jwks(rsa_jwk: dict) -> dict:
    """JWKS key set containing the test public key (public parts only)."""
    key = JsonWebKey.import_key(rsa_jwk, {'kty': 'RSA'})
    public = key.as_dict()
    for priv in ('d', 'p', 'q', 'dp', 'dq', 'qi'):
        public.pop(priv, None)
    return {'keys': [public]}


@pytest.fixture
def valid_jwt_token(rsa_jwk: dict, test_settings: Settings) -> str:
    """Create a valid JWT signed with the test private JWK via authlib."""
    now = int(time.time())
    payload = {
        'sub': 'test-officer-001',
        'iss': (
            f'{test_settings.auth.keycloak_server_url}/'
            f'realms/{test_settings.auth.keycloak_realm}'
        ),
        'aud': test_settings.auth.keycloak_client_id,
        'exp': now + 3600,
        'iat': now,
        'realm_access': {'roles': ['auditor', 'officer']},
    }
    jwt = JsonWebToken(algorithms=['RS256'])
    token = jwt.encode(header={'alg': 'RS256'}, payload=payload, key=rsa_jwk)
    return token.decode('utf-8') if isinstance(token, bytes) else str(token)


class MockCredentials:
    """Minimal stand-in for HTTPAuthorizationCredentials."""

    def __init__(self, token: str) -> None:
        self.credentials = token
        self.scheme = 'Bearer'


class TestPrincipal:
    def test_principal_stores_subject_and_roles(self) -> None:
        p = Principal(
            subject='user-1',
            realm_roles=frozenset({'officer'}),
            raw_claims={'sub': 'user-1'},
        )
        assert p.subject == 'user-1'
        assert p.realm_roles == frozenset({'officer'})

    def test_has_role_returns_true_for_matching_role(self) -> None:
        p = Principal(subject='user-1', realm_roles=frozenset({'auditor'}))
        assert p.has_role('auditor') is True

    def test_has_role_returns_false_for_non_matching_role(self) -> None:
        p = Principal(subject='user-1', realm_roles=frozenset({'officer'}))
        assert p.has_role('auditor') is False

    def test_has_role_with_empty_roles(self) -> None:
        p = Principal(subject='user-1')
        assert p.has_role('anything') is False

    def test_principal_is_frozen(self) -> None:
        p = Principal(subject='user-1')
        with pytest.raises(AttributeError):
            p.subject = 'different'


class TestJwksCache:
    @pytest.mark.asyncio
    async def test_get_fetches_jwks_from_correct_url(
        self, test_settings: Settings, valid_jwks: dict
    ) -> None:
        cache = _JwksCache(ttl_seconds=300)
        expected_url = (
            f'{test_settings.auth.keycloak_server_url}/realms/'
            f'{test_settings.auth.keycloak_realm}/protocol/openid-connect/certs'
        )

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=valid_jwks)
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx, 'AsyncClient', autospec=True) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await cache.get(test_settings)
            mock_client.get.assert_called_once_with(expected_url)
            assert result is not None

    @pytest.mark.asyncio
    async def test_cache_returns_cached_keys_on_second_call(
        self, test_settings: Settings, valid_jwks: dict
    ) -> None:
        cache = _JwksCache(ttl_seconds=300)

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=valid_jwks)
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx, 'AsyncClient', autospec=True) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            await cache.get(test_settings)
            await cache.get(test_settings)
            assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_refetches_after_ttl_expiry(
        self, test_settings: Settings, valid_jwks: dict
    ) -> None:
        cache = _JwksCache(ttl_seconds=0)

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=valid_jwks)
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx, 'AsyncClient', autospec=True) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            await cache.get(test_settings)
            await cache.get(test_settings)
            assert mock_client.get.call_count == 2


class TestGetCurrentPrincipal:
    @pytest.mark.asyncio
    async def test_valid_token_returns_principal(
        self, valid_jwt_token: str, test_settings: Settings, valid_jwks: dict
    ) -> None:
        """Happy path: valid token returns Principal."""
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=valid_jwks)
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx, 'AsyncClient', autospec=True) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            principal = await get_current_principal(
                MockCredentials(valid_jwt_token), test_settings
            )
            assert isinstance(principal, Principal)
            assert principal.subject == 'test-officer-001'
            assert 'auditor' in principal.realm_roles

    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self, test_settings: Settings) -> None:
        """REJECTED: token signed with wrong key -> 401."""
        wrong_key = JsonWebKey.generate_key('RSA', 2048, is_private=True).as_dict(
            is_private=True
        )
        now = int(time.time())
        payload = {
            'sub': 'bad-sig',
            'iss': (
                f'{test_settings.auth.keycloak_server_url}/'
                f'realms/{test_settings.auth.keycloak_realm}'
            ),
            'exp': now + 3600,
            'iat': now,
        }
        jwt = JsonWebToken(algorithms=['RS256'])
        bad_token = jwt.encode(header={'alg': 'RS256'}, payload=payload, key=wrong_key)
        bad_token_str = (
            bad_token.decode('utf-8')
            if isinstance(bad_token, bytes)
            else str(bad_token)
        )

        # Generate a DIFFERENT key pair for JWKS to ensure signature mismatch
        public_jwk = JsonWebKey.generate_key('RSA', 2048, is_private=False).as_dict()
        different_jwks = {'keys': [public_jwk]}

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=different_jwks)
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx, 'AsyncClient', autospec=True) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await get_current_principal(
                    MockCredentials(bad_token_str), test_settings
                )
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_issuer_rejected(
        self, rsa_jwk: dict, test_settings: Settings, valid_jwks: dict
    ) -> None:
        """REJECTED: valid signature but wrong issuer -> 401."""
        now = int(time.time())
        payload = {
            'sub': 'wrong-issuer',
            'iss': 'http://evil-keycloak/realms/evil-realm',
            'exp': now + 3600,
            'iat': now,
        }
        jwt = JsonWebToken(algorithms=['RS256'])
        token = jwt.encode(header={'alg': 'RS256'}, payload=payload, key=rsa_jwk)
        token_str = token.decode('utf-8') if isinstance(token, bytes) else str(token)

        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=valid_jwks)
        mock_response.raise_for_status = MagicMock()

        with patch.object(httpx, 'AsyncClient', autospec=True) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await get_current_principal(MockCredentials(token_str), test_settings)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_token_rejected(self, test_settings: Settings) -> None:
        """REJECTED: garbage token -> 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_principal(
                MockCredentials('this.is.not.a.jwt'), test_settings
            )
        assert exc_info.value.status_code == 401


class TestRequireRole:
    @pytest.mark.asyncio
    async def test_principal_with_required_role_passes(self) -> None:
        principal = Principal(subject='auditor-1', realm_roles=frozenset({'auditor'}))
        dep = require_role('auditor')
        result = await dep(principal)
        assert result is principal

    @pytest.mark.asyncio
    async def test_principal_without_required_role_rejected(self) -> None:
        principal = Principal(subject='officer-1', realm_roles=frozenset({'officer'}))
        dep = require_role('auditor')
        with pytest.raises(HTTPException) as exc_info:
            await dep(principal)
        assert exc_info.value.status_code == 403
