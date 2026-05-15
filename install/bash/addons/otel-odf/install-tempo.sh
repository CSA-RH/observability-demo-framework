#!/bin/bash
set -e 
CURRENT_NAMESPACE=obs-demo

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

# Deploy Tempo Operator
echo ...TEMPO OPERATOR AND TempoStack... 
#  - Operator installation
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-tempo-operator
spec: {}
EOF
if check_openshift_resource_exists Subscription tempo-product openshift-tempo-operator; then
  echo " - Tempo Operator already installed"
else
    cat <<EOF | oc create -f -
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  annotations:
    olm.providedAPIs: TempoMonolithic.v1alpha1.tempo.grafana.com,TempoStack.v1alpha1.tempo.grafana.com
  generateName: openshift-tempo-operator-
  namespace: openshift-tempo-operator
spec:
  upgradeStrategy: Default
EOF
  cat <<EOF | oc create -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  labels:
    operators.coreos.com/tempo-product.openshift-tempo-operator: ""    
    observability-demo-framework: 'operator'
  name: tempo-product
  namespace: openshift-tempo-operator
spec:
  channel: stable
  installPlanApproval: Automatic
  name: tempo-product
  source: redhat-operators
  sourceNamespace: openshift-marketplace
  startingCSV: tempo-operator.v0.20.0-3
EOF
  # Wait for the operator to be created and available. 
  wait_operator_to_be_installed operators.coreos.com/tempo-product.openshift-tempo-operator openshift-tempo-operator
fi
#   RBAC permissions
echo " - RBAC for Tempo"
cat <<EOF | oc apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: tempostack-traces-reader
  labels: 
    observability-demo-framework: rbac
rules:
- apiGroups:
  - tempo.grafana.com
  resourceNames:
  - traces
  resources:
  - '*'
  verbs:
  - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: tempostack-traces-reader
  labels:
    observability-demo-framework: rbac
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: tempostack-traces-reader
subjects:
- apiGroup: rbac.authorization.k8s.io
  kind: Group
  name: system:authenticated
EOF

cat <<EOF | oc apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: tempostack-traces-write  
  labels: 
    observability-demo-framework: rbac
rules:
- apiGroups:
  - tempo.grafana.com
  resourceNames:
  - traces
  resources:
  - obsdemo
  verbs:
  - create
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: tempostack-traces
  labels: 
    observability-demo-framework: rbac
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: tempostack-traces-write
subjects:
- kind: ServiceAccount
  name: otel-collector
  namespace: $CURRENT_NAMESPACE
EOF

TEMPO_OBC_NAME="tempo-noobaa-claim"
TEMPO_SECRET_NAME="tempo-storage-secret"

echo " - Creating ObjectBucketClaim (OBC) for Tempo"
cat <<EOF | oc apply -f -
apiVersion: objectbucket.io/v1alpha1
kind: ObjectBucketClaim
metadata:
  name: $TEMPO_OBC_NAME
  namespace: $CURRENT_NAMESPACE
spec:
  generateBucketName: tempo-data
  storageClassName: openshift-storage.noobaa.io
EOF

echo " - Waiting for Tempo ObjectBucketClaim to bind..."
oc wait --for=jsonpath='{.status.phase}'=Bound obc/$TEMPO_OBC_NAME -n $CURRENT_NAMESPACE --timeout=120s

echo " - Extracting credentials from Tempo OBC"
BUCKET_HOST=$(oc get configmap $TEMPO_OBC_NAME -n $CURRENT_NAMESPACE -o jsonpath='{.data.BUCKET_HOST}')
BUCKET_NAME=$(oc get configmap $TEMPO_OBC_NAME -n $CURRENT_NAMESPACE -o jsonpath='{.data.BUCKET_NAME}')
AWS_ACCESS_KEY_ID=$(oc get secret $TEMPO_OBC_NAME -n $CURRENT_NAMESPACE -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)
AWS_SECRET_ACCESS_KEY=$(oc get secret $TEMPO_OBC_NAME -n $CURRENT_NAMESPACE -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 -d)

# Hardcode port 80 for the internal HTTP endpoint
ENDPOINT="${BUCKET_HOST}:80"

echo " - Updating the backend S3 storage secret for Tempo (Port 80)"
cat <<EOF | oc apply -f - 
apiVersion: v1
kind: Secret
metadata:
  name: $TEMPO_SECRET_NAME
  namespace: $CURRENT_NAMESPACE
stringData:
  access_key_id: "${AWS_ACCESS_KEY_ID}"
  access_key_secret: "${AWS_SECRET_ACCESS_KEY}"
  bucket: "${BUCKET_NAME}"
  endpoint: "${ENDPOINT}"
type: Opaque
EOF

echo " - Tempo storage secret created successfully!"

#   RESOURCE TempoStack
echo " - Install/Configure TempoStack"
cat <<EOF | oc apply -f - 
apiVersion: tempo.grafana.com/v1alpha1
kind: TempoStack
metadata:
  name: escotilla
  namespace: $CURRENT_NAMESPACE
  labels:
    observability-demo-framework: traces
spec:
  tenants:
    authentication:
      - tenantId: obsdemo
        tenantName: obsdemo
    mode: openshift
  managementState: Managed
  serviceAccount: tempo-escotilla
  template:
    gateway:
      enabled: true
      ingress:
        route:
          termination: reencrypt
        type: route
    queryFrontend:
      component:
        replicas: 1
      jaegerQuery:        
        enabled: true        
        monitorTab:
          enabled: true
          prometheusEndpoint: 'https://thanos-querier.openshift-monitoring.svc.cluster.local:9091'
  observability:
    tracing:
      jaeger_agent_endpoint: 'localhost:6831'
  search:
    defaultResultLimit: 20  
  storage:
    secret:
      name: $TEMPO_SECRET_NAME
      type: s3
EOF