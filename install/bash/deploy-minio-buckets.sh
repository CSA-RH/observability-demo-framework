#!/bin/bash
source ./env.sh
set -o pipefail
SCRIPT_DIR="$(realpath "$(dirname "$0")")"

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
        image: minio/mc
        command: ["/bin/sh", "/runner/create-bucket.sh"]
        volumeMounts:
        - name: runner-vol
          mountPath: /runner
      restartPolicy: Never
      volumes: 
      - name: runner-vol
        configMap:
          name: script-minio
          defaultMode: 0555
EOF
)

JOB_NAME=$(echo "$MANIFEST" | oc create -f - -ojsonpath='{.metadata.name}')
echo JOB=$JOB_NAME

print_header "Waiting for script to finalize..."
oc wait job $JOB_NAME \
    --for=condition=Complete \
    --timeout=30s