#!/bin/bash
set -e

# Load environment
source ../env.sh

# Create or update the playbook to sync users
print_header "Create/Update playbook for syncing users..."
oc create configmap sync-users-playbook \
    --from-file=./playbook-sync-users.yml \
    -n $NAMESPACE \
    --dry-run=client \
    -oyaml \
    | oc apply -f -

# Service account for syncing users
print_header "Create or update service account obs-sync-users for user management"
export SA_SYNC_USERS=obs-sync-users
cat <<EOF | oc apply -f - 
apiVersion: v1
kind: ServiceAccount
metadata:
  name: $SA_SYNC_USERS
EOF
cat <<EOF | oc apply -f -
kind: Role
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: idp-configmap-automation-role    
rules:
- apiGroups: [""] 
  resources: ["configmaps"]
  verbs: ["get", "list", "watch", "patch", "update", "create"]
---
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: idp-configmap-automation-binding
subjects:
- kind: ServiceAccount
  name: $SA_SYNC_USERS
roleRef:
  kind: Role
  name: idp-configmap-automation-role
  apiGroup: rbac.authorization.k8s.io
EOF

cat <<EOF | oc apply -f -
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: idp-configmap-automation-clusterrole    
rules:
- apiGroups: [""]
  resources: ["namespaces"]
  verbs: ["get", "list", "watch", "delete", "update", "patch", "create"]
- apiGroups: ["rbac.authorization.k8s.io"]
  resources: ["clusterrolebindings"]
  verbs: ["get", "list", "watch", "delete", "update", "patch", "create"]
- apiGroups: ["", "image.openshift.io"] # Core API and OpenShift Image API groups
  resources: ["imagestreams/layers"]
  verbs: ["get"]
- apiGroups: ["opentelemetry.io"] # The specific API Group for the CRD
  resources: ["instrumentations"]   # The plural resource name
  verbs: ["get", "list", "watch", "delete", "update", "patch", "create"]
---
kind: ClusterRoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: idp-configmap-automation-clusterrolebinding
subjects:
- kind: ServiceAccount
  name: $SA_SYNC_USERS
  namespace: $NAMESPACE
roleRef:
  kind: ClusterRole
  name: idp-configmap-automation-clusterrole
  apiGroup: rbac.authorization.k8s.io
EOF

print_header "Create job..."
MANIFEST=$(cat <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  generateName: sync-users-
  labels: 
    observability-demo-framework: users
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 180  
  template:
    spec:      
      serviceAccountName:  $SA_SYNC_USERS
      containers:
      - name: ansible
        image: image-registry.openshift-image-registry.svc:5000/obs-demo/obs-sync-users
        command: ["ansible-playbook",  "/runner/playbook-sync-users.yml"]
        env:
        - name: KC_API_URL
          valueFrom:
            configMapKeyRef:
              name: idp-data
              key: endpoint
        - name: KC_API_CLIENT_ID
          valueFrom:
            configMapKeyRef:
              name: idp-data
              key: client_id
        - name: KC_API_CLIENT_SECRET
          valueFrom:
            configMapKeyRef:
              name: idp-data
              key: client_secret
        - name: KC_API_REALM
          valueFrom:
            configMapKeyRef:
              name: idp-data
              key: realm
        volumeMounts:
        - name: runner-vol
          mountPath: /runner
      restartPolicy: Never
      volumes: 
      - name: runner-vol
        configMap:
          name: sync-users-playbook
EOF
)
JOB_NAME=$(echo "$MANIFEST" | oc create -f - -ojsonpath='{.metadata.name}')
echo JOB=$JOB_NAME

print_header "Waiting for playbook execution pod to be ready..."
oc wait pod \
    --for=condition=Ready \
    --selector=job-name=$JOB_NAME \
    --timeout=30s

print_header "Playbook execution ..."
oc logs -f \
  $(oc get pod \
    --selector job-name=$JOB_NAME \
    --field-selector=status.phase=Running \
     -ojsonpath='{.items[0].metadata.name}')

