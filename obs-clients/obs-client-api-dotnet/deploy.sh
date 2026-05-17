#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$(realpath "$(dirname "$0")")"

# Create ImageStream for Observability dotnet
cat <<EOF | oc apply -f -
apiVersion: image.openshift.io/v1
kind: ImageStream
metadata:
  name: obs-client-dotnet
spec:
  lookupPolicy:
    local: true
EOF
# Create BuildConfig for kc-client
cat <<EOF | oc apply -f - 
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  labels:
    build: obs-client-dotnet-local
  name: obs-client-dotnet-local
spec:
  output:
    to:
      kind: ImageStreamTag
      name: obs-client-dotnet:latest
  source:
    binary: {}
    type: Binary
  strategy:
    dockerStrategy: 
      dockerfilePath: Dockerfile
    type: Docker
EOF
# Resources cleanup
rm -rf bin out obj
# Remove previous build objects
oc delete build --selector build=obs-client-dotnet-local > /dev/null 
# Start build for obs-client-dotnet
oc start-build obs-client-dotnet-local --from-file $SCRIPT_DIR
# Follow the logs until completion 
oc logs $(oc get build --selector build=obs-client-dotnet-local -oNAME) -f 