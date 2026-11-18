"""Background workflows behind the 202 Accepted endpoints. Each one records its progress in the
OperationStore and rolls back what it can when it fails."""
import asyncio
import inspect
from typing import Any, Dict

from services.interfaces import OperationStore, SimulationService, TenantService


async def _invoke_agent_delete_metrics(agent_manager, user_id: str):
    result = agent_manager.delete_metrics_definitions(user_id)
    if inspect.isawaitable(result):
        await result


def _set_running(operations: OperationStore, operation_id: str, message: str):
    operation = operations.get(operation_id)
    metadata = dict(operation.get("metadata") or {})
    metadata["message"] = message
    operations.update(operation_id, status="running", metadata=metadata)


def _without_user(tenants: TenantService, username: str):
    return [user for user in tenants.get_users() if user.get("username") != username]


async def run_user_create(operations: OperationStore, tenants: TenantService, operation_id: str,
                          user_payload: Dict[str, Any]):
    username = user_payload.get("username")
    try:
        _set_running(operations, operation_id, "Updating user registry and syncing with Keycloak")
        tenants.save_users(tenants.get_users() + [user_payload])

        if await asyncio.to_thread(tenants.sync_users):
            operations.update(operation_id, status="succeeded")
            return

        tenants.save_users(_without_user(tenants, username))
        operations.update(operation_id, status="failed", error="Keycloak user sync job failed")
    except Exception as exc:
        try:
            tenants.save_users(_without_user(tenants, username))
        except Exception:
            pass
        operations.update(operation_id, status="failed", error=str(exc))


async def run_user_delete(operations: OperationStore, tenants: TenantService, operation_id: str, user_id: str):
    previous_users = tenants.get_users()
    try:
        _set_running(operations, operation_id, "Removing user and syncing with Keycloak")
        tenants.save_users([user for user in previous_users if user.get("username") != user_id])

        if await asyncio.to_thread(tenants.sync_users):
            operations.update(operation_id, status="succeeded")
            return

        tenants.save_users(previous_users)
        operations.update(operation_id, status="failed", error="Keycloak user sync job failed after delete")
    except Exception as exc:
        try:
            tenants.save_users(previous_users)
        except Exception:
            pass
        operations.update(operation_id, status="failed", error=str(exc))


async def run_simulation_create(operations: OperationStore, simulations: SimulationService, operation_id: str,
                                user_id: str, payload: Dict[str, Any]):
    try:
        _set_running(operations, operation_id, "Creating agent deployments and monitoring resources")
        json_agents = await asyncio.to_thread(
            simulations.create_resources,
            user_id,
            payload["agents"],
            payload["user"]["monitoringType"],
        )
        simulations.save(user_id, payload)
        operations.update(operation_id, status="succeeded", result=json_agents)
    except Exception as exc:
        operations.update(operation_id, status="failed", error=str(exc))


async def run_simulation_delete(operations: OperationStore, simulations: SimulationService, operation_id: str,
                                user_id: str, agent_manager):
    try:
        _set_running(operations, operation_id, "Deleting simulation resources")
        await asyncio.to_thread(simulations.delete, user_id)
        await _invoke_agent_delete_metrics(agent_manager, user_id)
        operations.update(operation_id, status="succeeded")
    except Exception as exc:
        operations.update(operation_id, status="failed", error=str(exc))
