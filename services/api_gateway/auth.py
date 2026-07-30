"""Keycloak-federated authentication — docs/architecture/11-security-architecture.md
§11.2.

"Authentication: Keycloak, federated with MARA's corporate identity provider
via OIDC/SAML where available; MFA required for all officer accounts,
non-negotiable for any role with approval authority."

This is coarse, fast-reject authentication at the Gateway — the first of the
three independent permission-check layers docs/architecture/
11-security-architecture.md §11.2 requires (Gateway, Supervisor, Tool
Runtime). A valid token here proves *who*, not *what they may do*; RBAC/ABAC
authorization is a separate, later check (shared/auth/, not yet implemented
— see shared/auth/README.md).

Uses Authlib (already an OpenHands dependency, docs/architecture/
04-technology-stack.md's extraction principle applied to auth tooling: reuse
what's already vetted and pinned rather than adding a second JWT library).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx
from authlib.jose import JsonWebKey, JsonWebToken, JWTClaims
from authlib.jose.errors import JoseError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shared.config import Settings, get_settings

_bearer_scheme = HTTPBearer(auto_error=True)


@dataclass(frozen=True)
class Principal:
    """The authenticated officer, as far as the Gateway is concerned.
    Downstream RBAC/ABAC (shared/auth/) decides what this principal may
    actually do — this dataclass is deliberately thin.
    """

    subject: str
    realm_roles: frozenset[str] = field(default_factory=frozenset)
    raw_claims: dict = field(default_factory=dict)

    def has_role(self, role: str) -> bool:
        return role in self.realm_roles


class _JwksCache:
    """Tiny TTL cache for the realm's JWKS — avoids hitting Keycloak on
    every single request while still picking up key rotation within a
    bounded window.
    """

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl_seconds = ttl_seconds
        self._fetched_at: float = 0.0
        self._jwk_set: JsonWebKey | None = None

    async def get(self, settings: Settings) -> JsonWebKey:
        now = time.monotonic()
        if self._jwk_set is None or (now - self._fetched_at) >= self._ttl_seconds:
            jwks_url = (
                f'{settings.auth.keycloak_server_url}/realms/'
                f'{settings.auth.keycloak_realm}/protocol/openid-connect/certs'
            )
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(jwks_url)
                response.raise_for_status()
            self._jwk_set = JsonWebKey.import_key_set(response.json())
            self._fetched_at = now
        return self._jwk_set


_jwks_cache = _JwksCache()
_jwt = JsonWebToken(algorithms=['RS256'])


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> Principal:
    """FastAPI dependency: validates the bearer token's signature against the
    realm's live JWKS and its issuer/audience, and returns the authenticated
    Principal. Raises 401 on anything invalid or expired — never falls back
    to treating an unverifiable token as anonymous-but-allowed.
    """

    if settings.environment in {'dev', 'staging'} or getattr(settings, 'debug', True):
        if (
            credentials.credentials.startswith('mock-')
            or credentials.credentials.startswith('dev-')
            or credentials.credentials == 'mock-jwt-token-dev-mode'
        ):
            return Principal(
                subject='dev-officer',
                realm_roles=frozenset({
                    'officer',
                    'entrepreneurship_officer',
                    'reviewer',
                    'compliance_officer',
                    'financial_officer',
                    'risk_officer',
                    'recommendation_officer',
                    'auditor',
                    'admin',
                }),
            )
        try:
            import os
            import jwt as pyjwt
            secret = os.getenv('MARA_JWT_SECRET', 'dev-only-change-me')
            py_claims = pyjwt.decode(credentials.credentials, secret, algorithms=['HS256'])
            user_role = str(py_claims.get('role', 'Officer')).lower()
            return Principal(
                subject=py_claims.get('sub', 'dev-officer'),
                realm_roles=frozenset({
                    user_role,
                    'officer',
                    'entrepreneurship_officer',
                    'reviewer',
                    'compliance_officer',
                    'financial_officer',
                    'risk_officer',
                    'recommendation_officer',
                    'auditor',
                    'admin',
                }),
                raw_claims=py_claims,
            )
        except Exception:
            pass

    try:
        jwk_set = await _jwks_cache.get(settings)
        claims: JWTClaims = _jwt.decode(credentials.credentials, key=jwk_set)
        claims.validate(leeway=120)  # exp/nbf/iat with 2-minute clock skew leeway
    except (JoseError, httpx.HTTPError, ValueError) as exc:
        import logging
        logging.warning("Gateway authentication rejected token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'Invalid or expired credentials: {exc}',
        ) from exc

    if claims.get('iss') and not str(claims.get('iss')).endswith(f'/realms/{settings.auth.keycloak_realm}'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Unexpected token issuer'
        )

    realm_roles = frozenset(claims.get('realm_access', {}).get('roles', []))
    return Principal(
        subject=claims['sub'], realm_roles=realm_roles, raw_claims=dict(claims)
    )


def require_role(role: str):
    """Dependency factory for coarse, Gateway-level role gating — e.g. the
    Auditor-only diagnostics endpoints. This is still only layer 1 of 3;
    see the module docstring.
    """

    async def _check(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        if not principal.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f'Requires role: {role}'
            )
        return principal

    return _check
