export ARO_INFRASTRUCTURE_NAME=$(oc get infrastructure cluster -o jsonpath='{.status.infrastructureName}')
export CLUSTER_NAME=$(echo $ARO_INFRASTRUCTURE_NAME | sed 's/-[^-]*$//')
export HYPERSCALER_STORAGE_SECRET_TYPE=azure
export HYPERSCALER_STORAGE_CLASS=managed-csi

load_environment_storage_backend() {
  # Define variables for storage (ARO)  
  export STORAGE_RESOURCE_GROUP=$(az aro list --query "[?name=='$CLUSTER_NAME'].resourceGroup" -o tsv)
  export STORAGE_LOCATION=$(az aro show --name "$CLUSTER_NAME" --resource-group "$STORAGE_RESOURCE_GROUP" --query "location" -o tsv)
  export STORAGE_ACCOUNT_NAME="${ARO_INFRASTRUCTURE_NAME//-/}"
  echo "Loading loki backend environment"
  set +e
  az storage account show --name "$STORAGE_ACCOUNT_NAME" --resource-group "$STORAGE_RESOURCE_GROUP" &>/dev/null
  if [ $? -eq 0 ]; then
    echo "Found storage account: $STORAGE_ACCOUNT_NAME"
  else
    echo "No storage account found with name '$STORAGE_ACCOUNT_NAME'. Creating... "    
    az storage account create \
      --name "$STORAGE_ACCOUNT_NAME" \
      --resource-group "$STORAGE_RESOURCE_GROUP" \
      --location "$STORAGE_LOCATION" \
      --sku Standard_LRS \
      --kind StorageV2
    echo "Storage account '$STORAGE_ACCOUNT_NAME' created in region '$STORAGE_LOCATION'."
  fi
  set -e
  export STORAGE_ACCOUNT_KEY=$(az storage account keys list \
    --resource-group $STORAGE_RESOURCE_GROUP \
    --account-name $STORAGE_ACCOUNT_NAME \
    --query "[0].value" -o tsv)
}

# Storage account and container for TempoStack
get_tempo_storage_account() {
  echo " - Checking storage account for the backend (ARO)"
  if az storage account show --name "$STORAGE_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    echo " - Storage account '$STORAGE_ACCOUNT_NAME' exists."
  else
    echo " - Storage account '$STORAGE_ACCOUNT_NAME' does NOT exist."
    echo "   Creating..."
    # Create the storage account with a tag
    az storage account create \
      --name $STORAGE_ACCOUNT_NAME \
      --resource-group $RESOURCE_GROUP \
      --location $LOCATION \
      --sku Standard_LRS \
      --kind StorageV2 \
      --tags observability-demo-framework=storage
  fi  
}

load_tempo_storage_backend() {
  load_environment_storage_backend
  export STORAGE_CONTAINER_TEMPO="tempostack-container"
  echo "  - Checking the container in the storage account for Tempo"
  if az storage container show --name "$STORAGE_CONTAINER_TEMPO" --account-name "$STORAGE_ACCOUNT_NAME" --account-key "$STORAGE_ACCOUNT_KEY" &>/dev/null; then
      echo " - Container '$STORAGE_CONTAINER_TEMPO' exists in storage account '$STORAGE_ACCOUNT_NAME'."
  else
      echo " - Container '$STORAGE_CONTAINER_TEMPO' does NOT exist in storage account '$STORAGE_ACCOUNT_NAME'."
      echo "   Creating..."
      az storage container create \
        --name "$STORAGE_CONTAINER_TEMPO" \
        --account-name "$STORAGE_ACCOUNT_NAME" \
        --account-key "$STORAGE_ACCOUNT_KEY"
  fi  
  echo " - Checking the backend storage secret for Tempo"
  cat <<EOF | oc apply -f - 
kind: Secret
apiVersion: v1
metadata:
  name: tempo-storage-secret
  namespace: $CURRENT_NAMESPACE
data:
  account_key: $(echo -n $STORAGE_ACCOUNT_KEY | base64 -w 0)
  account_name: $(echo -n $STORAGE_ACCOUNT_NAME | base64 -w 0)
  container: $(echo -n $STORAGE_CONTAINER_TEMPO | base64 -w 0)
  environment: QXp1cmVHbG9iYWw=
type: Opaque
EOF
}

load_loki_storage_backend() {
  load_environment_storage_backend
  export STORAGE_CONTAINER_LOKI="lokistack-container"
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
  channel: stable-6.1
  installPlanApproval: Automatic
  name: loki-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
  startingCSV: loki-operator.v6.1.1
EOF
}
