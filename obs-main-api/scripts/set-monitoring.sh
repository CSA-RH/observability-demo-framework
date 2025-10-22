#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$(realpath "$(dirname "$0")")"
# Prerequisites
source $SCRIPT_DIR/env.sh

NAMESPACE="openshift-monitoring"
CONFIGMAP_NAME="cluster-monitoring-config"

# Get the current ConfigMap
CURRENT_CONFIG=$(oc get -n "$NAMESPACE" cm "$CONFIGMAP_NAME" -o json)

# Extract config.yaml and remove the newline
CONFIG_DATA=$(echo "$CURRENT_CONFIG" | jq -r '.data["config.yaml"]' | tr -d '\n')

# Check if enableUserMonitoring is already enabled
if echo "$CONFIG_DATA" | grep -q 'enableUserMonitoring: true'; then
  echo "enableUserMonitoring is already enabled."
else
  echo "enableUserMonitoring is not enabled. Enabling it now..."

  # Add enableUserMonitoring to the config.yaml using yq for YAML manipulation
  UPDATED_CONFIG=$(echo "$CONFIG_DATA" | yq eval '.enableUserMonitoring = true' -)

  # Construct the patch for the ConfigMap
  PATCH=$(cat <<EOF
{
  "data": {
    "config.yaml": "$(echo "$UPDATED_CONFIG" | sed ':a;N;$!ba;s/\n/\\n/g')"
  }
}
EOF
)

  # Apply the patch to the ConfigMap
  echo "$PATCH" | oc patch cm "$CONFIGMAP_NAME" -n "$NAMESPACE" --type=merge -p "$(cat)"

  echo "enableUserMonitoring has been enabled in YAML format."
fi
