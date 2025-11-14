#!/bin/bash

# -- Prerequisites check
oc whoami > /dev/null 2>&1
# Check the exit status of the previous command ($?)
if [ $? -ne 0 ]; then
    echo "ERROR: oc tool is not logged in or cannot connect to the cluster." >&2
    echo "Please run 'oc login' or ensure your current configuration is valid." >&2
    exit 1
fi

echo "Successfully verified oc login. Continuing script execution..."
 
export NAMESPACE=$(oc project -q)
export CURRENT_NAMESPACE=$NAMESPACE
export INFRASTRUCTURE=$(oc get infrastructure cluster -o jsonpath='{.status.platform}')

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

print_header () {
    echo ""
    echo "**"
    echo "** $1"
}