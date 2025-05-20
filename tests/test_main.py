from fastapi.testclient import TestClient

from app.main import fastapi_app as app


def test_app_instance__no_code():
    client = TestClient(app)
    response = client.get("/foo/")
    assert response.status_code == 404


def test_logging_configured():
    import logging

    logger = logging.getLogger()
    assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
