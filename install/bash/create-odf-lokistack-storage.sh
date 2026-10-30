#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="openshift-logging"
OBC_NAME="lokistack-storage"
LOKI_SECRET_NAME="loki-storage-secret"

echo "=== 1. Ensuring namespace ${NAMESPACE} exists ==="
oc get namespace "${NAMESPACE}" >/dev/null 2>&1 || oc create namespace "${NAMESPACE}"

echo "=== 2. Creating ObjectBucketClaim: ${OBC_NAME} in ${NAMESPACE} ==="
cat <<EOF | oc apply -f -
apiVersion: objectbucket.io/v1alpha1
kind: ObjectBucketClaim
metadata:
  name: ${OBC_NAME}
  namespace: ${NAMESPACE}
spec:
  generateBucketName: lokistack-bucket
  # Uncomment and specify if not using the cluster default storage class:
  storageClassName: openshift-storage.noobaa.io
EOF

echo "=== 3. Waiting for ObjectBucketClaim ${OBC_NAME} to be Bound ==="
RETRIES=30
until [[ $(oc get obc "${OBC_NAME}" -n "${NAMESPACE}" -o jsonpath='{.status.phase}' 2>/dev/null || true) == "Bound" ]]; do
  RETRIES=$((RETRIES - 1))
  if [[ $RETRIES -le 0 ]]; then
    echo "ERROR: Timed out waiting for OBC ${OBC_NAME} to become Bound."
    exit 1
  fi
  echo "Waiting for bucket provisioning... (${RETRIES} retries remaining)"
  sleep 3
done
echo "OBC ${OBC_NAME} is Bound!"

echo "=== 4. Extracting bucket parameters and credentials ==="
BUCKET_NAME=$(oc get cm "${OBC_NAME}" -n "${NAMESPACE}" -o jsonpath='{.data.BUCKET_NAME}')
BUCKET_HOST=$(oc get cm "${OBC_NAME}" -n "${NAMESPACE}" -o jsonpath='{.data.BUCKET_HOST}')
AWS_ACCESS_KEY_ID=$(oc get secret "${OBC_NAME}" -n "${NAMESPACE}" -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)
AWS_SECRET_ACCESS_KEY=$(oc get secret "${OBC_NAME}" -n "${NAMESPACE}" -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 -d)

# For internal ODF (s3.openshift-storage.svc), route via port 80 to bypass internal TLS CA verification
if [[ "${BUCKET_HOST}" == "s3.openshift-storage.svc" ]]; then
  ENDPOINT="http://s3.openshift-storage.svc:80"
else
  ENDPOINT="http://${BUCKET_HOST}:80"
fi

echo "Discovered Bucket Name : ${BUCKET_NAME}"
echo "Configuring Endpoint   : ${ENDPOINT}"

echo "=== 5. Creating LokiStack S3 Secret: ${LOKI_SECRET_NAME} ==="
# Delete existing secret if it exists to ensure a clean state
oc delete secret "${LOKI_SECRET_NAME}" -n "${NAMESPACE}" --ignore-not-found=true

# Note: Loki Operator expects 'bucketnames' (plural)
oc create secret generic "${LOKI_SECRET_NAME}" -n "${NAMESPACE}" \
  --from-literal=bucketnames="${BUCKET_NAME}" \
  --from-literal=endpoint="${ENDPOINT}" \
  --from-literal=access_key_id="${AWS_ACCESS_KEY_ID}" \
  --from-literal=access_key_secret="${AWS_SECRET_ACCESS_KEY}" \
  --from-literal=insecure="true" \
  --from-literal=insecure_skip_verify="true"

echo "=== Success! ==="
echo "Secret '${LOKI_SECRET_NAME}' is ready in namespace '${NAMESPACE}'."
