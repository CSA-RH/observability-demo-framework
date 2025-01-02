#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$(realpath "$(dirname "$0")")"
SOURCES_DIR=$SCRIPT_DIR/../app/

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

# Create ImageStream for Observability Demo API if not exists
if check_openshift_resource_exists ImageStream obs-main-api; then
  echo "ImageStream obs-main-api exists"
else
  cat <<EOF | oc apply -f -
apiVersion: image.openshift.io/v1
kind: ImageStream
metadata:
  name: obs-main-api
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
    build: obs-main-api
  name: obs-main-api
spec:
  output:
    to:
      kind: ImageStreamTag
      name: obs-main-api:latest
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
oc delete build --selector build=obs-main-api > /dev/null 
# Start build for obs-main-api
oc start-build obs-main-api --from-file $SOURCES_DIR
# Follow the logs until completion 
oc logs $(oc get build --selector build=obs-main-api -oNAME) -f 
# Check if a deployment already exists
if check_openshift_resource_exists Deployment obs-main-api; then
  # update deployment
  echo "Updating deployment..."
  oc set image \
    deployment/obs-main-api \
    obs-main-api=$(oc get istag obs-main-api:latest -o jsonpath='{.image.dockerImageReference}')
else
  echo "Creating deployment, service and route..."
  # Create deployment
  #oc create deploy obs-main-api --image=obs-main-api:latest
  oc create sa obs-main-api-sa
  #TODO Tailor backend permissions only to the resources they're using. 
  oc adm policy add-cluster-role-to-user cluster-admin -z obs-main-api-sa
  cat <<EOF | oc create -f - 
apiVersion: apps/v1
kind: Deployment
metadata:
  creationTimestamp: null
  labels:
    app: obs-main-api
  name: obs-main-api
spec:
  replicas: 1
  selector:
    matchLabels:
      app: obs-main-api
  strategy: {}
  template:
    metadata:
      creationTimestamp: null
      labels:
        app: obs-main-api
    spec:
      serviceAccountName: obs-main-api-sa
      containers:
      - image: obs-main-api:latest
        name: obs-main-api
EOF
  # Create service
  oc expose deploy/obs-main-api --port 8000
  # Create route
  cat <<EOF | oc apply -f - 
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  labels:
    app: obs-main-api
  name: obs-main-api
spec:
  port:
    targetPort: 8000
  to:
    kind: Service
    name: obs-main-api
  tls: 
    termination: edge
EOF
fi