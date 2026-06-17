from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid


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
