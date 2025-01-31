# Load environment
source ./vars.sh
export LOKISTACK_RESOURCE=loki
# Deploy Loki Operator
echo ...LOKI OPERATOR AND LokiStack... 
if check_openshift_resource_exists Subscription loki-operator openshift-operators-redhat; then
  echo " - Loki Operator already installed"
else
  cat <<EOF | oc create -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:    
  labels:
    operators.coreos.com/loki-operator.openshift-operators-redhat: ""
    observability-demo-framework: 'operator'
  name: loki-operator
  namespace: openshift-operators-redhat
spec:
  channel: stable-6.1
  installPlanApproval: Automatic
  name: loki-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
  startingCSV: loki-operator.v6.1.1
EOF
  # Wait for the operator to be created and available. 
  wait_operator_to_be_installed operators.coreos.com/loki-operator.openshift-operators-redhat openshift-operators-redhat
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

# TODO: needs refactoring
echo "  - Checking the container in the storage account for Loki"
if az storage container show --name "$STORAGE_CONTAINER_LOKI" --account-name "$STORAGE_ACCOUNT_NAME" --account-key "$STORAGE_ACCOUNT_KEY" &>/dev/null; then
    echo "-  Container '$STORAGE_CONTAINER_LOKI' exists in storage account '$STORAGE_ACCOUNT_NAME'."
else
    echo " - Container '$STORAGE_CONTAINER_LOKI' does NOT exist in storage account '$STORAGE_ACCOUNT_NAME'."
    echo "   Creating..."
    az storage container create \
      --name "$STORAGE_CONTAINER_LOKI" \
      --account-name "$STORAGE_ACCOUNT_NAME" \
      --account-key "$STORAGE_ACCOUNT_KEY"
fi

echo "  - Checking the backend storage secret for Loki"
cat <<EOF | oc apply -f - 
kind: Secret
apiVersion: v1
metadata:
  name: loki-storage-secret
  namespace: openshift-logging
data:
  account_key: $(echo -n $STORAGE_ACCOUNT_KEY | base64 -w 0)
  account_name: $(echo -n $STORAGE_ACCOUNT_NAME | base64 -w 0)
  container: $(echo -n $STORAGE_CONTAINER_LOKI | base64 -w 0)
  environment: QXp1cmVHbG9iYWw=
type: Opaque
EOF

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
      name: loki-storage-secret
      type: azure
  hashRing:
    type: memberlist
  size: 1x.demo
  storageClassName: managed-csi
EOF