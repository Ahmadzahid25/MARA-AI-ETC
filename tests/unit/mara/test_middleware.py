"""Unit tests for services/api_gateway/middleware.py — CorrelationIdMiddleware.

Verifies that the middleware correctly assigns, propagates, and echoes the
correlation ID header (X-MARA-Correlation-Id by default).
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from services.api_gateway.middleware import CorrelationIdMiddleware
from shared.config import get_settings


def _make_test_app() -> FastAPI:
    """Create a minimal FastAPI app with the CorrelationIdMiddleware
    installed and a single route that returns the correlation ID."""
    app = FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get('/test')
    async def test_endpoint(request: Request) -> dict[str, str]:
        return {'correlation_id': request.state.correlation_id}

    return app


class TestCorrelationIdMiddleware:
    """Tests for the correlation ID assignment and propagation."""

    def test_client_header_echoed_on_response(self) -> None:
        """When the client sends X-MARA-Correlation-Id, the response
        should echo the same header value."""
        app = _make_test_app()
        client = TestClient(app)
        cid = 'client-provided-id-123'

        response = client.get('/test', headers={'X-MARA-Correlation-Id': cid})

        assert response.status_code == 200
        assert response.headers.get('X-MARA-Correlation-Id') == cid

    def test_no_client_header_generates_uuid(self) -> None:
        """When the client sends NO correlation header, the middleware
        should generate a UUID and return it."""
        app = _make_test_app()
        client = TestClient(app)

        response = client.get('/test')

        assert response.status_code == 200
        cid = response.headers.get('X-MARA-Correlation-Id')
        assert cid is not None
        # Verify it's a valid UUID
        uuid_obj = uuid.UUID(cid)
        assert str(uuid_obj) == cid

    def test_correlation_id_available_in_request_state(self) -> None:
        """The correlation ID should be accessible via
        request.state.correlation_id in the downstream handler."""
        app = _make_test_app()
        client = TestClient(app)
        cid = 'state-check-id'

        response = client.get('/test', headers={'X-MARA-Correlation-Id': cid})

        assert response.status_code == 200
        assert response.json()['correlation_id'] == cid

    def test_multiple_requests_get_unique_ids(self) -> None:
        """Each request without a correlation header should get a unique
        generated ID."""
        app = _make_test_app()
        client = TestClient(app)

        response1 = client.get('/test')
        response2 = client.get('/test')

        cid1 = response1.headers.get('X-MARA-Correlation-Id')
        cid2 = response2.headers.get('X-MARA-Correlation-Id')
        assert cid1 != cid2

    def test_empty_header_treated_as_missing(self) -> None:
        """An empty header value should be treated the same as no header
        — generate a new UUID."""
        app = _make_test_app()
        client = TestClient(app)

        response = client.get('/test', headers={'X-MARA-Correlation-Id': ''})

        cid = response.headers.get('X-MARA-Correlation-Id')
        assert cid is not None
        assert cid != ''

    def test_correlation_header_name_matches_settings(self) -> None:
        """The default header name should match settings.gateway_correlation_header."""
        settings = get_settings()
        expected_header = settings.gateway_correlation_header
        assert expected_header == 'X-MARA-Correlation-Id'

        app = _make_test_app()
        client = TestClient(app)

        response = client.get('/test', headers={expected_header: 'header-name-test'})
        assert response.headers.get(expected_header) == 'header-name-test'
