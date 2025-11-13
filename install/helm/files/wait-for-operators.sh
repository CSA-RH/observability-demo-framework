#!/bin/bash
# Fail fast if any command fails, variables are unbound, or a pipe fails
set -e -u -o pipefail

# Read the list of *names* from the environment
# Example: "loki-operator tempo-product"
OPERATOR_LIST=${OPERATOR_LIST:-""}

if [ -z "$OPERATOR_LIST" ]; then
    echo "OPERATOR_LIST is not set. No operators to check. Exiting successfully."
    exit 0
fi

echo "Starting check for operators: $OPERATOR_LIST"

# Loop over each space-separated name in the list
for SUBSCRIPTION_NAME in $OPERATOR_LIST; do
    
    echo "--- Checking Operator: $SUBSCRIPTION_NAME ---"

    # 1. Find the Subscription and its namespace
    echo "Waiting for Subscription '$SUBSCRIPTION_NAME' to be created in any namespace..."
    OPERATOR_NAMESPACE=""
    start_time=$(date +%s)
    
    until [ -n "$OPERATOR_NAMESPACE" ]; do
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        if [ $elapsed -gt 300 ]; then
            echo "Error: Timeout waiting to find Subscription '$SUBSCRIPTION_NAME' in any namespace."
            exit 1
        fi
        
        # Search all namespaces (-A) for the subscription name.
        # Get the namespace from the output.
        # Take the first line (head -n 1) in case of duplicates.
        # '|| true' prevents the script from exiting if 'oc get' fails.
        OPERATOR_NAMESPACE=$(oc get subscription $SUBSCRIPTION_NAME -A --no-headers -o custom-columns=NS:.metadata.namespace 2>/dev/null | head -n 1 || true)
        
        if [ -z "$OPERATOR_NAMESPACE" ]; then
            echo "  Subscription '$SUBSCRIPTION_NAME' not found yet... waiting 10s"
            sleep 10
        fi
    done
    
    echo "Found Subscription '$SUBSCRIPTION_NAME' in namespace: $OPERATOR_NAMESPACE"

    # 2. Wait for the Subscription to report its 'currentCSV'
    echo "Waiting for Subscription '$SUBSCRIPTION_NAME' to report its CSV..."
    CSV_NAME=""
    start_time=$(date +%s)
    
    until [ -n "$CSV_NAME" ]; do
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        if [ $elapsed -gt 300 ]; then
            echo "Error: Timeout waiting for .status.currentCSV on $SUBSCRIPTION_NAME"
            exit 1
        fi
        
        CSV_NAME=$(oc get subscription $SUBSCRIPTION_NAME -n $OPERATOR_NAMESPACE -o jsonpath='{.status.currentCSV}' 2>/dev/null || true)
        
        if [ -z "$CSV_NAME" ]; then
            echo "  .status.currentCSV not found yet... waiting 10s"
            sleep 10
        fi
    done
    
    # 3. Wait for that specific CSV to be in phase 'Succeeded'
    echo "CSV name is: $CSV_NAME"
    echo "Waiting for CSV '$CSV_NAME' to be Succeeded..."
    oc wait csv $CSV_NAME -n $OPERATOR_NAMESPACE --for=condition=Succeeded --timeout=300s
    
    echo "✅ $SUBSCRIPTION_NAME is Succeeded."
    echo "--------------------------------------------------------"
done

echo "✅ All specified operators are healthy."