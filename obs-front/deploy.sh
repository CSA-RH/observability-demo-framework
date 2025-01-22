#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$(realpath "$(dirname "$0")")"
SOURCES_DIR=$SCRIPT_DIR/

export CURRENT_NAMESPACE=$(oc project -q)
echo CURRENT NAMESPACE=$CURRENT_NAMESPACE

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

# Create ImageStream for Observability Demo Frontend if not exists
if check_openshift_resource_exists ImageStream obs-front; then
  echo "ImageStream obs-front exists"
else
  cat <<EOF | oc apply -f -
apiVersion: image.openshift.io/v1
kind: ImageStream
metadata:
  name: obs-front
spec:
  lookupPolicy:
    local: true
EOF
  # Create BuildConfig for Observability Demo Frontend if not exists
  cat <<EOF | oc apply -f - 
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  labels:
    build: obs-front
  name: obs-front
spec:
  output:
    to:
      kind: ImageStreamTag
      name: obs-front:latest
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
oc delete build --selector build=obs-front > /dev/null 
# Get keycloak route
export route IDP_URL=https://$(oc get route --selector app=keycloak -ojsonpath='{.items[0].spec.host}')
# Retrieve and set .env variables for API address
export REACT_APP_API_URL=https://$(oc get route obs-main-api -ojsonpath='{.spec.host}')
cat <<EOF > $SOURCES_DIR/.env
REACT_APP_OBSERVABILITY_DEMO_API=${REACT_APP_API_URL}
REACT_APP_KEYCLOAK_URL=${IDP_URL}
REACT_APP_KEYCLOAK_REALM=csa
REACT_APP_KEYCLOAK_CLIENT_ID=webauth
EOF
# Start build for obs-front
oc start-build obs-front --from-file $SOURCES_DIR 
# Follow the logs until completion 
oc logs $(oc get build --selector build=obs-front -oNAME) -f 
# Check if a deployment already exists
if check_openshift_resource_exists Deployment obs-front; then
  # update deployment
  echo "Updating deployment..."
  oc set image \
    deployment/obs-front \
    obs-front=$(oc get istag obs-front:latest -o jsonpath='{.image.dockerImageReference}')
else
  echo "Creating deployment, service and route..."
  # Create deployment
  oc create deploy obs-front --image=obs-front:latest 
  # Create service
  oc expose deploy/obs-front --port 8080
  # Create route
  cat <<EOF | oc apply -f - 
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  labels:
    app: obs-front
  name: obs-front
spec:
  port:
    targetPort: 8080
  to:
    kind: Service
    name: obs-front
  tls: 
    termination: edge
EOF
fi