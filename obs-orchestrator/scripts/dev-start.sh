#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status, 
# if an undefined variable is used, or if a piped command fails.
set -euo pipefail

# --- CONFIGURATION & PATHS ---
SCRIPT_DIR="$(realpath "$(dirname "$0")")"
SOURCES_DIR="$(realpath "$SCRIPT_DIR/../app")"
CERTS_DIR="$SCRIPT_DIR/certs"
IMPORT_DIR="$SCRIPT_DIR/import"

# ANSI Color codes for clean logging
LOG_INFO="\033[1;34m[INFO]\033[0m"
LOG_SUCCESS="\033[1;32m[SUCCESS]\033[0m"
LOG_WARN="\033[1;33m[WARN]\033[0m"
LOG_ERROR="\033[1;31m[ERROR]\033[0m"

# --- HELPER FUNCTIONS ---
log() { echo -e "${LOG_INFO} $1"; }
success() { echo -e "${LOG_SUCCESS} $1"; }
warn() { echo -e "${LOG_WARN} $1"; }
error() { echo -e "${LOG_ERROR} $1"; >&2; exit 1; }

usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --mode [local|cluster]  Select backend deployment execution mode (Default: local)
  --force-certs           Force regeneration of SSL certificates
  -h, --help              Show this help message
EOF
    exit 0
}

# --- ARGUMENT PARSING ---
MODE="local"
FORCE_CERTS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            if [[ "$2" == "local" || "$2" == "cluster" ]]; then
                MODE="$2"
                shift 2
            else
                error "Invalid mode: $2. Choose 'local' or 'cluster'."
            fi
            ;;
        --force-certs)
            FORCE_CERTS=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            error "Unknown argument: $1. Use --help for usage."
            ;;
    esac
done

check_prereqs() {
    log "Checking system prerequisites..."
    command -v openssl >/dev/null 2>&1 || error "openssl is required but missing."
    command -v oc >/dev/null 2>&1 || error "OpenShift CLI (oc) is required but missing."
    command -v python3 >/dev/null 2>&1 || error "python3 is required but missing."
    
    if [ "$MODE" = "local" ]; then
        command -v podman >/dev/null 2>&1 || error "podman is required for local Keycloak."
    fi
    success "All prerequisites met."
}

# --- STEP 2: IDEMPOTENT CERTIFICATE GENERATION ---
generate_certs() {
    if [ "$FORCE_CERTS" = false ] && [ -f "$CERTS_DIR/rootCA.crt" ] && [ -f "$CERTS_DIR/keycloak.crt" ] && [ -f "$CERTS_DIR/keycloak.key" ]; then
        log "Valid certificates already exist. Skipping generation. (Use --force-certs to overwrite)"
        return 0
    fi

    log "Generating fresh local Development CA and Certificates..."
    mkdir -p "$CERTS_DIR"

    # 1. Root CA
    openssl genrsa -out "$CERTS_DIR/rootCA.key" 4096
    openssl req -x509 -new -nodes -key "$CERTS_DIR/rootCA.key" -sha256 -days 1024 \
      -out "$CERTS_DIR/rootCA.crt" \
      -subj "/CN=LocalMock-Root-CA" \
      -addext "basicConstraints=critical,CA:TRUE" \
      -addext "keyUsage=critical,keyCertSign,cRLSign"

    # 2. Keycloak CSR
    openssl genrsa -out "$CERTS_DIR/keycloak.key" 2048
    openssl req -new -key "$CERTS_DIR/keycloak.key" -out "$CERTS_DIR/keycloak.csr" \
      -subj "/CN=localhost"

    # 3. SAN Extension config
    cat <<EOF > "$CERTS_DIR/keycloak.ext"
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = keycloak
IP.1 = 127.0.0.1
EOF

    # 4. Sign Certificate
    openssl x509 -req -in "$CERTS_DIR/keycloak.csr" -CA "$CERTS_DIR/rootCA.crt" -CAkey "$CERTS_DIR/rootCA.key" \
      -CAcreateserial -out "$CERTS_DIR/keycloak.crt" -days 365 -sha256 -extfile "$CERTS_DIR/keycloak.ext"

    # Clean up signing artifacts
    rm -f "$CERTS_DIR/keycloak.csr" "$CERTS_DIR/keycloak.ext" "$CERTS_DIR/rootCA.srl"
    success "Certificates successfully generated in $CERTS_DIR"
}

# --- STEP 3: IDEMPOTENT KEYCLOAK RUNNER ---
start_local_keycloak() {
    log "Ensuring local Keycloak container is configured..."
    mkdir -p "$IMPORT_DIR"

    # Check if port 8443 is blocked by something else
    if exec 6<>/dev/tcp/127.0.0.1/8443; then
        exec 6>&- # close connection
        # If port is open, check if it's our container or a conflict
        if ! podman ps --format "{{.Names}}" | grep -q "^keycloak-local$"; then
            error "Port 8443 is already in use by another process!"
        fi
    fi

    if podman ps --format "{{.Names}}" | grep -q "^keycloak-local$"; then
        log "Keycloak container is already running."
    elif podman ps -a --format "{{.Names}}" | grep -q "^keycloak-local$"; then
        log "Keycloak container exists but is stopped. Restarting..."
        podman start keycloak-local
    else
        log "Spinning up new Keycloak container via Podman..."
        podman run -d --name keycloak-local \
          -p 8443:8443 \
          -v "$CERTS_DIR:/opt/keycloak/certs:Z" \
          -v "$IMPORT_DIR:/opt/keycloak/data/import:Z" \
          -e KEYCLOAK_ADMIN=admin \
          -e KEYCLOAK_ADMIN_PASSWORD=admin \
          -e KC_HTTPS_CERTIFICATE_FILE=/opt/keycloak/certs/keycloak.crt \
          -e KC_HTTPS_CERTIFICATE_KEY_FILE=/opt/keycloak/certs/keycloak.key \
          quay.io/keycloak/keycloak:latest \
          start-dev --import-realm
    fi
    success "Local Keycloak is ready."
    warn "CSA realm admin password default: 9Hzg3p6z43yT+HBzNzM0Eg=="
}

# --- STEP 4: PYTHON ENVIRONMENT SETUP ---
setup_python_env() {
    log "Configuring Virtual Environment..."
    if [ ! -d "$SOURCES_DIR/.venv" ]; then
        log "Virtual environment not found. Creating one..."
        python3 -m venv "$SOURCES_DIR/.venv"
    fi
    
    # Activate safely inside the subshell execution
    source "$SOURCES_DIR/.venv/bin/activate"
    
    log "Syncing python dependencies..."
    pip3 install --upgrade pip --quiet
    pip3 install -r "$SOURCES_DIR/requirements.txt" --quiet
}

# --- STEP 5: OPENSHIFT CONFIGURATION ---
configure_openshift() {
    log "Checking OpenShift Cluster Connection..."
    if ! oc whoami > /dev/null 2>&1; then
        error "You are not logged into an OpenShift Cluster. Run 'oc login' first."
    fi
    
    log "Switching to OpenShift project 'obs-demo'..."
    oc project obs-demo
}

# --- MAIN EXECUTION ---
check_prereqs
configure_openshift

if [ "$MODE" = "local" ]; then
    log "--- Starting environment in LOCAL BACKEND mode ---"
    generate_certs
    start_local_keycloak
    setup_python_env

    # Source local structural environment configurations if file exists
    if [ -f "$SCRIPT_DIR/env.sh" ]; then
        source "$SCRIPT_DIR/env.sh"
    fi

    log "Launching FastAPI application via Uvicorn..."
    export KEYCLOAK_ISSUER=https://localhost:8443/realms/csa
    export REQUESTS_CA_BUNDLE="${CERTS_DIR}/rootCA.crt"
    export SSL_CERT_FILE="${CERTS_DIR}/rootCA.crt"
    export AGENT_MANAGER=mock
    export LEASE_HOLDER_IDENTITY="local-dev-${USER:-dev}-$$"

    # Execute uvicorn (replacing the bash process cleanly)
    exec uvicorn main:app \
        --reload \
        --app-dir "$SOURCES_DIR" \
        --reload-dir "$SOURCES_DIR" \
        --host 0.0.0.0 \
        --port 8000 \
        --ssl-keyfile="${CERTS_DIR}/keycloak.key" \
        --ssl-certfile="${CERTS_DIR}/keycloak.crt"
else
    log "--- Starting environment in CLUSTER BACKEND mode ---"
    warn "Local Keycloak and local FastAPI will not be started."
    success "OpenShift project contextualized to 'obs-demo'. You can now start your React frontend pointed to your cluster route."
fi