#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$(realpath "$(dirname "$0")")"
SOURCES_DIR=$SCRIPT_DIR/../app/
CA_DIR=$SCRIPT_DIR/../temp-ca/

# Prerequisites
source $SCRIPT_DIR/env.sh
source $SOURCES_DIR/.venv/bin/activate
pip3 install -r "$SCRIPT_DIR/../app/requirements.txt"

# Get the CA certificate for request validation
rm -rf "${CA_DIR}"
mkdir -p "${CA_DIR}"
oc get secret keycloak-route-ca-secret -o json \
  | jq -r ".data[\"ca.crt\"]" \
  | base64 -d > "${CA_DIR}/ca.crt"
# Run the FastAPI app using Uvicorn, specifying the app directory

export KEYCLOAK_ISSUER=https://$(oc get route --selector app=keycloak -ojsonpath='{.items[0].spec.host}')/realms/csa
export REQUESTS_CA_BUNDLE="${CA_DIR}/ca.crt"
export AGENT_MANAGER=mock
uvicorn main:app --reload --app-dir "$SCRIPT_DIR/../app" --reload-dir "$SCRIPT_DIR/../app"