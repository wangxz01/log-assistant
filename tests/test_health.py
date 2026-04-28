from app.api.routes.health import health_check
from app.main import app


def test_health_route_is_registered() -> None:
    paths = {route.path for route in app.routes}

    assert "/health" in paths


def test_health_check_response() -> None:
    response = health_check()

    assert response.status == "ok"
    assert isinstance(response.ai_configured, bool)
