#!/bin/bash
set -e 
# Load environment
source ./env.sh
if [[ $INFRASTRUCTURE = "AWS"  ]]; then
  source ./env-rosa.sh
else
  source ./env-aro.sh
fi

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
  startingCSV: tempo-operator.v0.18.0-1
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

# Storage backend in Hyperscaler
load_tempo_storage_backend

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
      name: tempo-storage-secret
      type: $HYPERSCALER_STORAGE_SECRET_TYPE
EOF