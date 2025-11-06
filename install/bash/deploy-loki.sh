#!/bin/bash
set -e 
# Load environment
source ./env.sh
if [[ $INFRASTRUCTURE = "AWS"  ]]; then
  source ./env-rosa.sh
else
  source ./env-aro.sh
fi

export LOKISTACK_RESOURCE=loki

# Load Hyperscaler infrastructure
#  - Operator installation 
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-logging
spec: {}
EOF
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-loki-operator
spec: {}
EOF
load_loki_storage_backend

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

# Wait for the operator to be created and available. 
wait_operator_to_be_installed operators.coreos.com/loki-operator.openshift-loki-operator openshift-loki-operator

#   RESOURCE LokiStack
echo " - Install/Configure LokiStack"
cat <<EOF | oc apply -f -
apiVersion: loki.grafana.com/v1
kind: LokiStack
metadata:
  name: $LOKISTACK_RESOURCE
  namespace: openshift-logging
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
      name: lokistack-minio
      type: s3
  hashRing:
    type: memberlist
  size: 1x.demo
  storageClassName: $HYPERSCALER_STORAGE_CLASS
EOF