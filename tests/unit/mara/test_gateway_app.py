"""Unit tests for services/api_gateway/app.py — FastAPI app factory.

Verifies that create_app() builds the correct application structure with
the right middleware, routers, metadata, and error handling.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from services.api_gateway.app import create_app


class TestCreateApp:
    """Tests for the app factory function."""

    def setup_method(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_app_title_and_version(self) -> None:
        """The app should have the correct title and version metadata."""
        assert self.app.title == 'MARA AI-ETC API Gateway'
        assert self.app.version == '0.1.0-milestone1'

    def test_health_endpoint_returns_ok(self) -> None:
        """GET /healthz should return 200 with status ok."""
        response = self.client.get('/healthz')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert data['service'] == 'mara-api-gateway'

    def test_health_endpoint_no_auth_required(self) -> None:
        """The health endpoint should be accessible without any
        authentication — it's the liveness check that must answer
        before a client can authenticate at all."""
        response = self.client.get('/healthz')
        assert response.status_code == 200

    def test_correlation_middleware_installed(self) -> None:
        """The CorrelationIdMiddleware should be installed and generating
        correlation IDs for every response."""
        response = self.client.get('/healthz')
        assert 'X-MARA-Correlation-Id' in response.headers
        cid = response.headers['X-MARA-Correlation-Id']
        assert cid is not None
        assert len(cid) > 0

    def test_diagnostics_router_mounted(self) -> None:
        """The diagnostics router should be mounted at /diagnostics."""
        routes = [route.path for route in self.app.routes]
        assert '/diagnostics/synthetic-trace' in routes

    def test_otel_instrumentation_does_not_crash(self) -> None:
        """OTel instrumentation is optional (handles ImportError gracefully
        in telemetry.py). The app should still function without it."""
        # Re-create the app (app factory already ran create_app above)
        # Just verify the app routes include expected endpoints
        paths = {route.path for route in self.app.routes}
        assert '/healthz' in paths
        assert '/diagnostics/synthetic-trace' in paths

    def test_404_on_unknown_route(self) -> None:
        """Unknown routes should return 404, not crash."""
        response = self.client.get('/nonexistent-route')
        assert response.status_code == 404

    def test_app_info_route_descriptions(self) -> None:
        """Routes should have basic OpenAPI metadata."""
        openapi = self.app.openapi()
        paths = openapi.get('paths', {})
        assert '/healthz' in paths
        # healthz should be a GET endpoint
        assert 'get' in paths['/healthz']
