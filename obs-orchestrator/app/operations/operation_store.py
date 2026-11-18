from abc import abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

from services.interfaces import OperationStore


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_operation(operation_type: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = utc_now_iso()
    return {
        "id": str(uuid.uuid4()),
        "type": operation_type,
        "status": "pending",
        "metadata": metadata or {},
        "error": None,
        "result": None,
        "createdAt": now,
        "updatedAt": now,
    }


class DocumentOperationStore(OperationStore):
    """All operations kept in one JSON document `{id: operation}`; subclasses load/save it."""

    @abstractmethod
    def _load(self) -> Dict[str, Any]:
        ...

    @abstractmethod
    def _save(self, operations: Dict[str, Any]) -> None:
        ...

    def _operations(self) -> Dict[str, Any]:
        operations = self._load()
        return operations if isinstance(operations, dict) else {}

    def create(self, operation_type: str, metadata: Dict[str, Any] | None = None) -> str:
        operations = self._operations()
        operation = new_operation(operation_type, metadata)
        operations[operation["id"]] = operation
        self._save(operations)
        return operation["id"]

    def get(self, operation_id: str) -> Dict[str, Any] | None:
        return self._operations().get(operation_id)

    def update(self, operation_id: str, status: str | None = None, error: str | None = None,
               result: Any = None, metadata: Dict[str, Any] | None = None) -> None:
        operations = self._operations()
        operation = operations.get(operation_id)
        if operation is None:
            raise KeyError(f"Operation '{operation_id}' not found")
        if status is not None:
            operation["status"] = status
        if error is not None:
            operation["error"] = error
        if result is not None:
            operation["result"] = result
        if metadata is not None:
            operation["metadata"] = metadata
        operation["updatedAt"] = utc_now_iso()
        self._save(operations)
