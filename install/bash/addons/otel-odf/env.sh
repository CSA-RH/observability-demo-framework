#!/bin/bash

export GLOBAL_ROOT_NAMESPACE=${NAMESPACE:-"obs-demo"}
export GLOBAL_SCRIPT_DIR="$(realpath "$(dirname "$0")")"
export GLOBAL_LOGGING_NAMESPACE="openshift-logging"
export GLOBAL_LOKISTACK_RESOURCE="${LOKISTACK_RESOURCE:-logging-loki}"

# Function to check if a resource exists
check_openshift_resource_exists() {
    local resource_type="$1"
    local resource_name="$2"
    local resource_namespace="$3"

    if oc get $resource_type $resource_name -n $resource_namespace >/dev/null 2>&1; then
        return 0  # True: resource exists
    else
        return 1  # False: resource does not exist
    fi
}

wait_operator_to_be_installed() {
    local operator_label="$1"
    local operator_namespace="$2"

    echo "Waiting for Operator CSV labelled as $operator_label to be created..."
    while [[ $(oc get csv -n "$operator_namespace" -l "$operator_label" 2>/dev/null | wc -l) -le 1 ]]; do
        sleep 5
    done

    oc wait --for=jsonpath='{.status.phase}'=Succeeded csv -n "$operator_namespace" -l "$operator_label" --timeout=300s
}