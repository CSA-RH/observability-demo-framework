from fastapi import APIRouter, Depends  # type: ignore

import dependencies as deps
from auth import get_current_user

router = APIRouter(prefix="/api/v1", tags=["cluster-info"])


@router.get("/escotilla")
async def get_escotilla_info(current_user: dict = Depends(get_current_user)):
    #TODO: Improve server error handling (balance mock and cluster)
    return deps.cluster_connector.get_cluster_info(current_user)
