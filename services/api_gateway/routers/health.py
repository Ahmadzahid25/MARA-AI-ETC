"""Liveness/readiness — no auth required (this is the one Gateway endpoint
that must answer before an officer can authenticate at all)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=['health'])


@router.get('/healthz')
async def healthz() -> dict[str, str]:
    return {'status': 'ok', 'service': 'mara-api-gateway'}
