#!/bin/bash
set -e

# Ensure everything is properly configured
source ./bootstrap.sh

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

