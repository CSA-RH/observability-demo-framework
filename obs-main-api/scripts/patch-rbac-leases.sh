#!/usr/bin/env bash
# Patch obs-main-api Role to allow Kubernetes Lease locks for user sync serialization.
set -euo pipefail

NAMESPACE="${1:-obs-demo}"

echo "Patching obs-main-api-role in namespace ${NAMESPACE}..."

oc apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: obs-main-api-role
  namespace: ${NAMESPACE}
  labels:
    observability-demo-framework: rbac
rules:
  - apiGroups: ["route.openshift.io"]
    resources: ["routes"]
    verbs: ["list"]
  - apiGroups: ["batch"]
    resources: ["jobs"]
    verbs: ["create", "watch", "get"]
  - apiGroups: ["batch"]
    resources: ["jobs/status"]
    verbs: ["get"]
  - apiGroups: ["coordination.k8s.io"]
    resources: ["leases"]
    verbs: ["create", "get", "list", "watch", "update", "patch", "delete"]
  - apiGroups: ["grafana.integreatly.org"]
    resources: ["grafanadatasources"]
    verbs: ["create", "get", "list", "watch", "delete", "patch", "update"]
EOF

echo "Verifying lease permission for obs-main-api-sa..."
oc auth can-i get leases \
  --as="system:serviceaccount:${NAMESPACE}:obs-main-api-sa" \
  -n "${NAMESPACE}"

echo "Done. Restart obs-main-api pod if it was already running:"
echo "  oc rollout restart deployment/obs-main-api -n ${NAMESPACE}"
