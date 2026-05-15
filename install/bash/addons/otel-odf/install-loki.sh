#!/bin/bash

export NAMESPACE=$(oc project -q)
export CURRENT_NAMESPACE=$NAMESPACE

# Function to check if a resource exists
check_openshift_resource_exists() {
    local resource_type="$1"
    local resource_name="$2"
    local resource_namespace="$3"

    if [ -z "$3" ]; then
      NAMESPACE="$CURRENT_NAMESPACE"
    else
      NAMESPACE="$3"
    fi

    if oc get $resource_type $resource_name -n $NAMESPACE >/dev/null 2>&1; then
        return 0  # True: resource exists
    else
        return 1  # False: resource does not exist
    fi
}

install_loki_subscription() {  
  cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:    
  labels:
    operators.coreos.com/loki-operator.openshift-loki-operator: ""
    observability-demo-framework: 'operator'
  name: loki-operator
  namespace: openshift-loki-operator
spec:
  channel: stable-6.3
  installPlanApproval: Automatic
  name: loki-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace  
EOF
}

wait_operator_to_be_installed() {
    local operator_label="$1"
    local operator_namespace="$2"

    # Wait for CSV to be created
    echo "Waiting for Operator CSV labelled as $operator_label to be created..."
    while [[ $(oc get csv -n "$operator_namespace" -l "$operator_label" 2>/dev/null | wc -l) -le 1 ]]; do
        sleep 5
    done

    # Wait for CSV to be in 'Succeeded' state
    oc wait --for=jsonpath='{.status.phase}'=Succeeded csv -n "$operator_namespace" -l "$operator_label" --timeout=300s
}

# Create namespaces
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-logging
  labels: 
    openshift.io/cluster-monitoring: "true"
spec: {}
EOF
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-loki-operator
spec: {}
EOF

# Deploy Loki Operator
echo "...LOKI OPERATOR AND LokiStack..."
if check_openshift_resource_exists Subscription loki-operator openshift-loki-operator; then
  echo " - Loki Operator already installed"
else
  cat <<EOF | oc create -f -
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  annotations:
    olm.providedAPIs: AlertingRule.v1.loki.grafana.com,LokiStack.v1.loki.grafana.com,RecordingRule.v1.loki.grafana.com,RulerConfig.v1.loki.grafana.com
  generateName: openshift-loki-operator-
  namespace: openshift-loki-operator
spec:
  upgradeStrategy: Default
EOF
  install_loki_subscription
fi

# Create Service Account for loki collector
export SA_COLLECTOR=loki-collector
cat <<EOF | oc apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: $SA_COLLECTOR
  namespace: openshift-logging
EOF

# Grant permissions to the service account
#   RBAC permissions
echo " - RBAC for Loki"
cat <<EOF | oc apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: logging-collector-logs-writer
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: logging-collector-logs-writer
subjects:
- kind: ServiceAccount
  name: $SA_COLLECTOR
  namespace: openshift-logging
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:  
  name: collect-application-logs
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: collect-application-logs
subjects:
- kind: ServiceAccount
  name: $SA_COLLECTOR
  namespace: openshift-logging
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: collect-audit-logs
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: collect-audit-logs
subjects:
- kind: ServiceAccount
  name: $SA_COLLECTOR
  namespace: openshift-logging
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: collect-infrastructure-logs
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: collect-infrastructure-logs
subjects:
- kind: ServiceAccount
  name: $SA_COLLECTOR
  namespace: openshift-logging
EOF

# Wait for the operator to be created and available. 
wait_operator_to_be_installed operators.coreos.com/loki-operator.openshift-loki-operator openshift-loki-operator

#   RESOURCE LokiStack
LOKISTACK_RESOURCE="${LOKISTACK_RESOURCE:-logging-loki}"
NAMESPACE="openshift-logging"
OBC_NAME="loki-noobaa-claim"
LOKI_SECRET_NAME="lokistack-noobaa-secret"

echo " - Creating ObjectBucketClaim (OBC) for NooBaa"
cat <<EOF | oc apply -f -
apiVersion: objectbucket.io/v1alpha1
kind: ObjectBucketClaim
metadata:
  name: $OBC_NAME
  namespace: $NAMESPACE
spec:
  generateBucketName: loki-data
  storageClassName: openshift-storage.noobaa.io
EOF

echo " - Waiting for ObjectBucketClaim to bind (this may take a minute)..."
oc wait --for=jsonpath='{.status.phase}'=Bound obc/$OBC_NAME -n $NAMESPACE --timeout=120s

echo " - Extracting credentials from OBC"
AWS_ACCESS_KEY_ID=$(oc get secret $OBC_NAME -n $NAMESPACE -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)
AWS_SECRET_ACCESS_KEY=$(oc get secret $OBC_NAME -n $NAMESPACE -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 -d)
BUCKET_NAME=$(oc get configmap $OBC_NAME -n $NAMESPACE -o jsonpath='{.data.BUCKET_NAME}')
BUCKET_HOST=$(oc get configmap $OBC_NAME -n $NAMESPACE -o jsonpath='{.data.BUCKET_HOST}')
BUCKET_PORT=$(oc get configmap $OBC_NAME -n $NAMESPACE -o jsonpath='{.data.BUCKET_PORT}')

# Construct the NooBaa endpoint (NooBaa internal routes are typically HTTPS)
ENDPOINT="https://${BUCKET_HOST}:${BUCKET_PORT}"

echo " - Creating LokiStack compatible secret"
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: $LOKI_SECRET_NAME
  namespace: $NAMESPACE
stringData:
  access_key_id: "${AWS_ACCESS_KEY_ID}"
  access_key_secret: "${AWS_SECRET_ACCESS_KEY}"
  bucketnames: "${BUCKET_NAME}"
  endpoint: "${ENDPOINT}"
EOF

echo " - Install/Configure LokiStack"
cat <<EOF | oc apply -f -
apiVersion: loki.grafana.com/v1
kind: LokiStack
metadata:
  name: $LOKISTACK_RESOURCE
  namespace: $NAMESPACE
spec:
  tenants:
    mode: openshift-logging    
  managementState: Managed
  limits:
    global:
      queries:
        queryTimeout: 3m
  storage:
    schemas:
      - effectiveDate: '2022-06-01'
        version: v12
      - effectiveDate: "2024-04-02"
        version: v13
    secret:
      name: $LOKI_SECRET_NAME
      type: s3
  hashRing:
    type: memberlist
  size: 1x.demo
  storageClassName: ocs-external-storagecluster-ceph-rbd
EOF

echo " - LokiStack configuration complete!"