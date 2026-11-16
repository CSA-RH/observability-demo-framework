"""obs-orchestrator API: app setup only. Endpoints live in `routers/`, auth in `auth.py`,
backend singletons (cluster connector, agent manager) in `dependencies.py`."""
import os

from fastapi import FastAPI, HTTPException, Request                 # type: ignore
from fastapi.middleware.cors import CORSMiddleware                  # type: ignore
from fastapi.responses import JSONResponse                          # type: ignore

import dependencies  # noqa: F401  (instantiates the backends at startup)
from routers import alerts, cluster_info, metrics, operations, simulation, users

#RESPONSE CODES HERE: https://github.com/Kludex/starlette/blob/main/starlette/status.py


def get_cors_allowed_origins():
    """Comma-separated `CORS_ALLOWED_ORIGINS` (the obs-console URL). Unset: any origin, with a warning."""
    value = os.environ.get('CORS_ALLOWED_ORIGINS', '')
    origins = [origin.strip().rstrip('/') for origin in value.split(',') if origin.strip()]
    if not origins:
        print("WARNING[cors]: CORS_ALLOWED_ORIGINS is not set; allowing any origin")
        return ["*"]
    return origins


app = FastAPI()
# The console sends the token in the Authorization header, not in cookies: no credentials needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    print(f"Handling exception for request: {request} ")
    return JSONResponse(status_code=500, content={"message": "Internal server error", "details": str(exc)})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    print(f"Handling HTTP exception for request: {request} ")
    return JSONResponse(status_code=exc.status_code, content={"message": exc.detail})


for router_module in (cluster_info, users, operations, simulation, metrics, alerts):
    app.include_router(router_module.router)
