#!/bin/bash
set -euo pipefail # Fail fast on errors

SCRIPT_DIR="$(realpath "$(dirname "$0")")"
RELEASE_NAME="obs-minio"
NAMESPACE="minio"
CHART_NAME="minio/minio"
VALUES_FILE="$SCRIPT_DIR/obs-values.yaml"

# 1. Add and update the repo (idempotent)
echo "Adding Helm repositories..."
helm repo add minio https://charts.min.io/
helm repo update

# 2. Run the idempotent install/upgrade
echo "Upgrading/Installing $RELEASE_NAME in $NAMESPACE..."
helm upgrade "$RELEASE_NAME" "$CHART_NAME" \
  --install \
  --atomic \
  --wait \
  --namespace "$NAMESPACE" \
  --create-namespace \
  -f "$VALUES_FILE"

echo "✅ Helm release $RELEASE_NAME is up to date."

# Create route for minio. 
cat <<EOF | oc apply -f -
apiVersion: route.openshift.io/v1
kind: Route
metadata: 
  labels:
    app: minio    
  name: obs-minio-console
  namespace: minio
spec:
  port:
    targetPort: 9001
  tls:
    termination: edge
  to:
    kind: Service
    name: obs-minio-console
    weight: 100
  wildcardPolicy: None
EOF

echo "   MinIO console address: https://$(oc get route obs-minio-console -n minio -ojsonpath='{.spec.host}')"

oc create configmap script-minio \
    --from-file create-bucket.sh=${SCRIPT_DIR}/scripts/create-minio-buckets.sh \
    -oyaml \
    --dry-run=client | oc apply -f - 

MANIFEST=$(cat <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  generateName: minio-buckets-
  labels: 
    observability-demo-framework: bootstrap
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 180  
  template:
    spec:      
      containers:
      - name: minio-bootstrap
        image: curlimages/curl
        command: ["/bin/sh",  "-c", "chmod +x /runner/create-minio-buckets.sh; /runner/create-minio-buckets.sh"]       
        volumeMounts:
        - name: runner-vol
          mountPath: /runner
      restartPolicy: Never
      volumes: 
      - name: runner-vol
        configMap:
          name: script-minio
EOF
)

JOB_NAME=$(echo "$MANIFEST" | oc create -f - -ojsonpath='{.metadata.name}')
echo JOB=$JOB_NAME

print_header "Waiting for script to finalize..."
oc wait pod \
    --for=condition=Completed \
    --selector=job-name=$JOB_NAME \
    --timeout=30s