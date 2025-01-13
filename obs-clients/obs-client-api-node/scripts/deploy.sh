#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$(realpath "$(dirname "$0")")"
SOURCES_DIR=$SCRIPT_DIR/../

echo CURRENT NAMESPACE=$(oc project -q)
# Function to check if a resource exists
check_openshift_resource_exists() {
    local resource_type="$1"
    local resource_name="$2"    

    if oc get $resource_type $resource_name >/dev/null 2>&1; then
        return 0  # True: resource exists
    else
        return 1  # False: resource does not exist
    fi
}

# Create ImageStream for Observability Demo Client API (NodeJS)
cat <<EOF | oc apply -f -
apiVersion: image.openshift.io/v1
kind: ImageStream
metadata:
  name: obs-client-node
spec:
  lookupPolicy:
    local: true
EOF
# Create BuildConfig for Observability Demo Client API 
cat <<EOF | oc apply -f - 
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  labels:
    build: obs-client-node
  name: obs-client-node
spec:
  output:
    to:
      kind: ImageStreamTag
      name: obs-client-node:latest
  source:
    binary: {}
    type: Binary
  strategy:
    dockerStrategy: 
      dockerfilePath: Dockerfile
    type: Docker
EOF
# Resources cleanup
rm -rf build node_modules package-lock.json .env
# Remove previous build objects
oc delete build --selector build=obs-client-node > /dev/null 
# Start build for obs-client-node
oc start-build obs-client-node --from-file $SOURCES_DIR
# Follow the logs until completion 
oc logs $(oc get build --selector build=obs-client-node -oNAME) -f 