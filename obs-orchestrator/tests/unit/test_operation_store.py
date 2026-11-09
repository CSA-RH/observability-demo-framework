from datetime import datetime

from operations.operation_store import new_operation


def test_new_operation_defaults():
    operation = new_operation("user-create", {"username": "abc"})
    assert operation["type"] == "user-create"
    assert operation["status"] == "pending"
    assert operation["metadata"] == {"username": "abc"}
    assert operation["error"] is None and operation["result"] is None
    assert operation["createdAt"] == operation["updatedAt"]
    assert datetime.fromisoformat(operation["createdAt"]).tzinfo is not None


def test_new_operation_ids_are_unique_and_metadata_defaults_to_empty():
    first, second = new_operation("x"), new_operation("x")
    assert first["id"] != second["id"]
    assert first["metadata"] == {}
