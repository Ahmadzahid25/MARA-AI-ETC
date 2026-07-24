"""Maps the typed tool-error taxonomy (docs/architecture/06-tool-architecture.md
§6.1) to HTTP responses — the Gateway boundary where a typed internal error
becomes a client-facing status code, per docs/architecture/02-system-architecture.md
§2.2's "no business logic lives here" not extending to "no error translation
either": routers still need to answer *something* other than a bare 500.

Only imports from ``shared/`` (``shared.schemas.tooling``), consistent with
every other file in this package — agent-specific errors (e.g.
``agents.document_agent.ExtractionParsingError``) are not mapped here and
fall through to FastAPI's default 500; narrowing that is a follow-up once
there's a shared, agent-independent error base to catch instead of an
ever-growing per-agent import list.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from shared.schemas.tooling import (
    ToolError,
    ToolExternalServiceError,
    ToolInputError,
    ToolPermissionError,
    ToolTimeoutError,
)

_STATUS_BY_ERROR: dict[type[ToolError], int] = {
    ToolInputError: status.HTTP_400_BAD_REQUEST,
    ToolPermissionError: status.HTTP_403_FORBIDDEN,
    ToolTimeoutError: status.HTTP_504_GATEWAY_TIMEOUT,
    ToolExternalServiceError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


def to_http_exception(exc: ToolError) -> HTTPException:
    for error_type, http_status in _STATUS_BY_ERROR.items():
        if isinstance(exc, error_type):
            return HTTPException(status_code=http_status, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
    )
