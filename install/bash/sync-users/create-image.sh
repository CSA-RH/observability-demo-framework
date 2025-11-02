#!/bin/bash
set -e

# Load environment
source ../env.sh

# Get the directory where the Dockerfile is located
SCRIPT_DIR="$(realpath "$(dirname "$0")")"
SOURCES_DIR=$SCRIPT_DIR/job-image/

# Create Ansible main image with dependencies for improving User Synchronization jobs start
print_header "Create Ansible main image with dependencies for improving User Synchronization jobs start"
# Create ImageStream for Observability Demo API if not exists
export SYNC_USERS_IMAGE_STREAM=obs-sync-users
if check_openshift_resource_exists ImageStream $SYNC_USERS_IMAGE_STREAM; then
  echo "ImageStream obs-main-api exists"
else
  cat <<EOF | oc apply -f -
apiVersion: image.openshift.io/v1
kind: ImageStream
metadata:
  name: $SYNC_USERS_IMAGE_STREAM
  labels: 
    observability-demo-framework: 'users'
spec:
  lookupPolicy:
    local: true
EOF
  # Create BuildConfig for Observability Demo API if not exists
  cat <<EOF | oc apply -f - 
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  labels:
    build: $SYNC_USERS_IMAGE_STREAM
    observability-demo-framework: 'cicd'
  name: $SYNC_USERS_IMAGE_STREAM
spec:
  output:
    to:
      kind: ImageStreamTag
      name: $SYNC_USERS_IMAGE_STREAM:latest
  source:
    binary: {}
    type: Binary
  strategy:
    dockerStrategy: 
      dockerfilePath: Dockerfile
    type: Docker
EOF
fi
  
# Remove previous build objects
oc delete build --selector build=$SYNC_USERS_IMAGE_STREAM > /dev/null 
# Start build for obs-sync-users
oc start-build $SYNC_USERS_IMAGE_STREAM --from-file $SOURCES_DIR
# Follow the logs until completion 
oc logs $(oc get build --selector build=$SYNC_USERS_IMAGE_STREAM -oNAME) -f