#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$(realpath "$(dirname "$0")")"
SOURCES_DIR=$SCRIPT_DIR/../app/

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

# Create ImageStream for Observability Demo API if not exists
if check_openshift_resource_exists ImageStream obs-main-api; then
  echo "ImageStream obs-main-api exists"
else
  cat <<EOF | oc apply -f -
apiVersion: image.openshift.io/v1
kind: ImageStream
metadata:
  name: obs-main-api
  labels: 
    observability-demo-framework: 'cicd'
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
    observability-demo-framework: 'cicd'
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
  
  # Customize backend permissions (to sa obs-main-api-sa) to match only the used resources.
  # - Create service account obs-main-api-sa
  oc create sa obs-main-api-sa
  # - Create role and clusterrole for service account
  cat <<EOF | oc apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: obs-main-api-role
  labels:
    observability-demo-framework: 'rbac'
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["create", "delete", "get", "list", "watch"]
  - apiGroups: ["monitoring.coreos.com"]
    resources: ["servicemonitors", "prometheusrules"]
    verbs: ["create", "delete", "get", "list", "watch"]
  - apiGroups: [""]
    resources: ["services"]
    verbs: ["create", "delete", "get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["secrets", "configmaps"]
    verbs: ["create", "delete", "get", "list", "watch", "patch"]
  - apiGroups: ["route.openshift.io"]
    resources: ["routes"]
    verbs: ["list"]
EOF

  cat <<EOF | oc apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: obs-main-api-clusterrole
  labels:
    observability-demo-framework: 'rbac'
rules:
  - apiGroups: ["config.openshift.io"]
    resources: ["consoles"]
    verbs: ["get"]
EOF
  # - Create role binding (obs-main-api-role and obs-main-api-clusterrole to obs-main-api-sa)
  cat <<EOF | oc apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: obs-main-api-rolebinding
  labels:
    observability-demo-framework: 'rbac'
subjects:
  - kind: ServiceAccount
    name: obs-main-api-sa
    namespace: $CURRENT_NAMESPACE
roleRef:
  kind: Role
  name: obs-main-api-role
  apiGroup: rbac.authorization.k8s.io
EOF
  cat <<EOF | oc apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: obs-main-api-clusterrolebinding
  labels:
    observability-demo-framework: 'rbac'
subjects:
  - kind: ServiceAccount
    name: obs-main-api-sa
    namespace: $CURRENT_NAMESPACE
roleRef:
  kind: ClusterRole
  name: obs-main-api-clusterrole
  apiGroup: rbac.authorization.k8s.io
EOF
  # Create deployment
  export route IDP_ISSUER=https://$(oc get route --selector app=keycloak -ojsonpath='{.items[0].spec.host}')/realms/csa
  cat <<EOF | oc create -f - 
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: obs-main-api
    observability-demo-framework: 'backend'
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
        observability-demo-framework: 'backend'
    spec:
      serviceAccountName: obs-main-api-sa
      volumes:
      - name: keycloak-route-ca-secret
        secret:
          secretName: keycloak-route-ca-secret
          defaultMode: 420
      containers:
      - image: obs-main-api:latest
        name: obs-main-api
        volumeMounts:
        - name: keycloak-route-ca-secret
          readOnly: true
          mountPath: /etc/ssl/keycloak
        env:
        - name: KEYCLOAK_ISSUER
          value: $IDP_ISSUER
        - name: REQUESTS_CA_BUNDLE
          value: /etc/ssl/keycloak/ca.crt
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
    observability-demo-framework: 'backend'
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