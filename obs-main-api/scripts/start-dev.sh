#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$(realpath "$(dirname "$0")")"
SOURCES_DIR=$SCRIPT_DIR/../app/
CERTS_DIR=$SCRIPT_DIR/certs

#TODO: Integrate generate certs and podman keycloak

# Prerequisites
source $SCRIPT_DIR/env.sh
source $SOURCES_DIR/.venv/bin/activate

oc project obs-demo
pip3 install -r "$SCRIPT_DIR/../app/requirements.txt"

# Run the FastAPI app using Uvicorn, specifying the app directory
export KEYCLOAK_ISSUER=https://localhost:8443/realms/csa
export REQUESTS_CA_BUNDLE="${CERTS_DIR}/rootCA.crt"
export SSL_CERT_FILE="${CERTS_DIR}/rootCA.crt"
export AGENT_MANAGER=mock
uvicorn main:app \
    --reload \
    --app-dir "$SCRIPT_DIR/../app" \
    --reload-dir "$SCRIPT_DIR/../app" \
    --ssl-keyfile=${CERTS_DIR}/keycloak.key \
    --ssl-certfile=${CERTS_DIR}/keycloak.crt