export CURRENT_NAMESPACE=$(oc project -q)
# Define variables for storage
export STORAGE_ACCOUNT_NAME="obsdemopalma"
export STORAGE_RESOURCE_GROUP="aro-palma"
export STORAGE_LOCATION="germanywestcentral"
export STORAGE_CONTAINER_LOKI="lokistack-container"
export STORAGE_CONTAINER_TEMPO="tempostack-container"
export STORAGE_ACCOUNT_KEY=$(az storage account keys list \
  --resource-group $STORAGE_RESOURCE_GROUP \
  --account-name $STORAGE_ACCOUNT_NAME \
  --query "[0].value" -o tsv)

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

# Storage account and container for TempoStack
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