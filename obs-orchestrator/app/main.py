"""obs-orchestrator API: app setup only. Endpoints live in `routers/`, auth in `auth.py`,
backend singletons (cluster connector, agent manager) in `dependencies.py`, configuration in
`settings.py`."""
import logging

from fastapi import FastAPI, HTTPException, Request                 # type: ignore
from fastapi.encoders import jsonable_encoder                      # type: ignore
from fastapi.exceptions import RequestValidationError              # type: ignore
from fastapi.middleware.cors import CORSMiddleware                  # type: ignore
from fastapi.responses import JSONResponse                          # type: ignore

from logging_config import setup_logging
from settings import Settings, settings

# Before importing the backends, so their startup messages use the configured format.
setup_logging(settings.log_level, settings.log_format)

import dependencies  # noqa: E402,F401  (instantiates the backends at startup)
from routers import alerts, cluster_info, metrics, operations, simulation, users  # noqa: E402

log = logging.getLogger(__name__)

#RESPONSE CODES HERE: https://github.com/Kludex/starlette/blob/main/starlette/status.py


def get_cors_allowed_origins(config: Settings = settings):
    """`CORS_ALLOWED_ORIGINS` (the obs-console URL). Unset: any origin, with a warning."""
    origins = config.cors_origins
    if not origins:
        log.warning("CORS_ALLOWED_ORIGINS is not set; allowing any origin")
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
    log.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=exc)
    return JSONResponse(status_code=500, content={"message": "Internal server error", "details": str(exc)})


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    level = logging.ERROR if exc.status_code >= 500 else logging.INFO
    log.log(level, f"{request.method} {request.url.path} -> {exc.status_code}: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"message": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Same shape as the other errors ({"message": ...}), which is what the console displays.
    errors = exc.errors()
    summary = "; ".join(
        f"{'.'.join(str(p) for p in error['loc'] if p != 'body') or 'body'}: {error['msg']}" for error in errors
    )
    return JSONResponse(
        status_code=422,
        content={"message": f"Invalid request: {summary}", "details": jsonable_encoder(errors)},
    )


for router_module in (cluster_info, users, operations, simulation, metrics, alerts):
    app.include_router(router_module.router)
