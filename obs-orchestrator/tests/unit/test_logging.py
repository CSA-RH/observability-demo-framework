"""JSON log lines and the levels used by the API error handlers."""
import json
import logging

from logging_config import JsonFormatter


def record(msg, level=logging.INFO, exc_info=None):
    return logging.LogRecord("cluster_connector.X", level, __file__, 1, msg, None, exc_info)


def test_json_line_has_queryable_fields():
    line = json.loads(JsonFormatter().format(record("Deployment cook-1 created ✅")))
    assert line["level"] == "INFO"
    assert line["logger"] == "cluster_connector.X"
    assert line["message"] == "Deployment cook-1 created ✅"
    assert line["ts"].endswith("+00:00")
    assert "exception" not in line


def test_json_line_includes_traceback():
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        import sys
        line = json.loads(JsonFormatter().format(record("failed", logging.ERROR, sys.exc_info())))
    assert "RuntimeError: boom" in line["exception"]


def test_client_errors_are_info_not_error(client, caplog):
    with caplog.at_level(logging.INFO, logger="main"):
        client.get("/api/v1/operations/does-not-exist")
    [entry] = [r for r in caplog.records if r.name == "main"]
    assert entry.levelno == logging.INFO
    assert entry.getMessage() == "GET /api/v1/operations/does-not-exist -> 404: Operation not found"


def test_unhandled_errors_are_logged_with_traceback(client, caplog, monkeypatch):
    import dependencies as deps

    def boom(user, is_admin=False):
        raise RuntimeError("cluster unreachable")

    monkeypatch.setattr(deps.capabilities, "get_cluster_info", boom)
    with caplog.at_level(logging.INFO, logger="main"):
        assert client.get("/api/v1/escotilla").status_code == 500
    [entry] = [r for r in caplog.records if r.name == "main"]
    assert entry.levelno == logging.ERROR
    assert entry.exc_info is not None
