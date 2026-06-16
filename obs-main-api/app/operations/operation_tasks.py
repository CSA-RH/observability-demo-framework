import asyncio
from typing import Any, Dict


async def run_user_create(cluster_connector, operation_id: str, user_payload: Dict[str, Any]):
    username = user_payload.get("username")
    try:
        cluster_connector.update_operation(operation_id, status="running")
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
    except Exception as e:
        try:
            users = [
                user for user in cluster_connector.get_users_json()
                if user.get("username") != username
            ]
            cluster_connector.update_users_json(users)
        except Exception:
            pass
        cluster_connector.update_operation(operation_id, status="failed", error=str(e))


async def run_user_delete(cluster_connector, operation_id: str, user_id: str):
    previous_users = cluster_connector.get_users_json()
    try:
        cluster_connector.update_operation(operation_id, status="running")
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
    except Exception as e:
        try:
            cluster_connector.update_users_json(previous_users)
        except Exception:
            pass
        cluster_connector.update_operation(operation_id, status="failed", error=str(e))


async def run_simulation_create(
    cluster_connector,
    operation_id: str,
    user_id: str,
    payload: Dict[str, Any],
):
    try:
        cluster_connector.update_operation(operation_id, status="running")
        json_agents = await cluster_connector.create_simulation_resources(
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
    except Exception as e:
        cluster_connector.update_operation(operation_id, status="failed", error=str(e))
