#!/bin/bash
set -euo pipefail

# Build obs-front via OpenShift BuildConfig and deploy to the active `oc` cluster.

SCRIPT_DIR="$(realpath "$(dirname "$0")")"
SOURCES_DIR=$SCRIPT_DIR/

export CURRENT_NAMESPACE=$(oc project -q)
echo "CURRENT NAMESPACE=$CURRENT_NAMESPACE"

check_openshift_resource_exists() {
    oc get "$1" "$2" >/dev/null 2>&1
}

resolve_route_url() {
    local route_name="$1"
    local host
    host="$(oc get route "$route_name" -o jsonpath='{.spec.host}' 2>/dev/null || true)"
    if [ -z "$host" ]; then
        echo "ERROR: Route '$route_name' not found in namespace $CURRENT_NAMESPACE" >&2
        exit 1
    fi
    echo "https://${host}"
}

resolve_keycloak_url() {
    local host

    host="$(oc get route --selector app=keycloak -o jsonpath='{.items[0].spec.host}' 2>/dev/null || true)"
    if [ -n "$host" ]; then
        echo "https://${host}"
        return
    fi

    host="$(oc get route -o jsonpath='{range .items[*]}{.spec.host}{"\n"}{end}' 2>/dev/null | grep -E "^oauth-" | head -1 || true)"
    if [ -n "$host" ]; then
        echo "https://${host}"
        return
    fi

    host="$(oc get cm idp-data -o jsonpath='{.data.endpoint}' 2>/dev/null | sed -E 's#^https?://##' || true)"
    if [ -n "$host" ]; then
        echo "https://${host}"
        return
    fi

    echo "ERROR: Could not discover Keycloak route (tried app=keycloak, oauth-*, idp-data)" >&2
    exit 1
}

wait_for_build() {
    local build_name="$1"
    echo "Waiting for build ${build_name} to complete..."
    if ! oc wait --for=condition=Complete --timeout=15m "build/${build_name}"; then
        echo "ERROR: Build ${build_name} failed." >&2
        oc logs "build/${build_name}" || true
        exit 1
    fi
}

export VITE_API_URL="$(resolve_route_url obs-main-api)"
export IDP_URL="$(resolve_keycloak_url)"

echo "Building frontend with:"
echo "  VITE_OBSERVABILITY_DEMO_API=${VITE_API_URL}"
echo "  VITE_KEYCLOAK_URL=${IDP_URL}"

# .env.production is uploaded with the binary context (not gitignored).
cat <<EOF > "${SOURCES_DIR}/.env.production"
VITE_OBSERVABILITY_DEMO_API=${VITE_API_URL}
VITE_KEYCLOAK_URL=${IDP_URL}
VITE_KEYCLOAK_REALM=csa
VITE_KEYCLOAK_CLIENT_ID=webauth
EOF

if ! check_openshift_resource_exists ImageStream obs-front; then
    oc apply -f - <<EOF
apiVersion: image.openshift.io/v1
kind: ImageStream
metadata:
  name: obs-front
  labels:
    observability-demo-framework: 'cicd'
spec:
  lookupPolicy:
    local: true
EOF
fi

oc apply -f - <<EOF
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  labels:
    build: obs-front-local
    observability-demo-framework: 'cicd'
  name: obs-front-local
spec:
  output:
    to:
      kind: ImageStreamTag
      name: obs-front:latest
  source:
    binary: {}
    type: Binary
  strategy:
    dockerStrategy:
      dockerfilePath: Dockerfile.local
      buildArgs:
        - name: VITE_OBSERVABILITY_DEMO_API
          value: "${VITE_API_URL}"
        - name: VITE_KEYCLOAK_URL
          value: "${IDP_URL}"
        - name: VITE_KEYCLOAK_REALM
          value: "csa"
        - name: VITE_KEYCLOAK_CLIENT_ID
          value: "webauth"
    type: Docker
EOF

oc delete build --selector build=obs-front-local > /dev/null 2>&1 || true

build_name="$(oc start-build obs-front-local --from-dir="${SOURCES_DIR}" --no-cache -o name | sed 's|build.build.openshift.io/||')"
oc logs -f "build/${build_name}"
wait_for_build "${build_name}"

if check_openshift_resource_exists Deployment obs-front; then
    echo "Updating deployment..."
    oc set image \
        deployment/obs-front \
        obs-front="$(oc get istag obs-front:latest -o jsonpath='{.image.dockerImageReference}')"
    oc rollout status deployment/obs-front --timeout=5m
else
    echo "Creating deployment, service and route..."
    oc create deploy obs-front --image=obs-front:latest
    oc label deploy obs-front observability-demo-framework=frontend
    oc expose deploy/obs-front --port 8080
    oc label service obs-front observability-demo-framework=frontend
    oc apply -f - <<EOF
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  labels:
    app: obs-front
    observability-demo-framework: frontend
  name: obs-front
spec:
  port:
    targetPort: 8080
  to:
    kind: Service
    name: obs-front
  tls:
    termination: edge
EOF
    oc rollout status deployment/obs-front --timeout=5m
fi

rm -f "${SOURCES_DIR}/.env.production"

echo "Done. Open https://$(oc get route obs-front -o jsonpath='{.spec.host}')"
