import asyncio
import inspect
from typing import Any, Dict


async def _invoke_agent_delete_metrics(agent_manager, user_id: str):
    result = agent_manager.delete_metrics_definitions(user_id)
    if inspect.isawaitable(result):
        await result


def _set_running(cluster_connector, operation_id: str, message: str):
    operation = cluster_connector.get_operation(operation_id)
    metadata = dict(operation.get("metadata") or {})
    metadata["message"] = message
    cluster_connector.update_operation(operation_id, status="running", metadata=metadata)


async def run_user_create(cluster_connector, operation_id: str, user_payload: Dict[str, Any]):
    username = user_payload.get("username")
    try:
        _set_running(cluster_connector, operation_id, "Updating user registry and syncing with Keycloak")
        users = cluster_connector.get_users_json()
        users.append(user_payload)
        cluster_connector.update_users_json(users)

        success = await asyncio.to_thread(cluster_connector.sync_users)
        if success:
            cluster_connector.update_operation(operation_id, status="succeeded")
            return

        users = [
            user for user in cluster_connector.get_users_json()
            if user.get("username") != username
        ]
        cluster_connector.update_users_json(users)
        cluster_connector.update_operation(
            operation_id,
            status="failed",
            error="Keycloak user sync job failed",
        )
    except Exception as exc:
        try:
            users = [
                user for user in cluster_connector.get_users_json()
                if user.get("username") != username
            ]
            cluster_connector.update_users_json(users)
        except Exception:
            pass
        cluster_connector.update_operation(operation_id, status="failed", error=str(exc))


async def run_user_delete(cluster_connector, operation_id: str, user_id: str):
    previous_users = cluster_connector.get_users_json()
    try:
        _set_running(cluster_connector, operation_id, "Removing user and syncing with Keycloak")
        new_users_list = [
            user for user in previous_users
            if user.get("username") != user_id
        ]
        cluster_connector.update_users_json(new_users_list)

        success = await asyncio.to_thread(cluster_connector.sync_users)
        if success:
            cluster_connector.update_operation(operation_id, status="succeeded")
            return

        cluster_connector.update_users_json(previous_users)
        cluster_connector.update_operation(
            operation_id,
            status="failed",
            error="Keycloak user sync job failed after delete",
        )
    except Exception as exc:
        try:
            cluster_connector.update_users_json(previous_users)
        except Exception:
            pass
        cluster_connector.update_operation(operation_id, status="failed", error=str(exc))


async def run_simulation_create(
    cluster_connector,
    operation_id: str,
    user_id: str,
    payload: Dict[str, Any],
):
    try:
        _set_running(cluster_connector, operation_id, "Creating agent deployments and monitoring resources")
        json_agents = await asyncio.to_thread(
            cluster_connector.create_simulation_resources,
            user_id,
            payload["agents"],
            payload["user"]["monitoringType"],
        )
        cluster_connector.save_simulation(user_id, payload)
        cluster_connector.update_operation(
            operation_id,
            status="succeeded",
            result=json_agents,
        )
    except Exception as exc:
        cluster_connector.update_operation(operation_id, status="failed", error=str(exc))


async def run_simulation_delete(cluster_connector, operation_id: str, user_id: str, agent_manager):
    try:
        _set_running(cluster_connector, operation_id, "Deleting simulation resources")
        await asyncio.to_thread(cluster_connector.delete_simulation, user_id)
        await _invoke_agent_delete_metrics(agent_manager, user_id)
        cluster_connector.update_operation(operation_id, status="succeeded")
    except Exception as exc:
        cluster_connector.update_operation(operation_id, status="failed", error=str(exc))
