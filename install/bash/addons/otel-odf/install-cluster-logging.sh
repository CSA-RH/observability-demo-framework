#!/bin/bash

# Ensure we are working in the correct namespace context
export LOGGING_NAMESPACE="openshift-logging"

# Function to check if a resource exists
check_openshift_resource_exists() {
    local resource_type="$1"
    local resource_name="$2"
    local resource_namespace="$3"

    if oc get $resource_type $resource_name -n $resource_namespace >/dev/null 2>&1; then
        return 0  # True: resource exists
    else
        return 1  # False: resource does not exist
    fi
}

wait_operator_to_be_installed() {
    local operator_label="$1"
    local operator_namespace="$2"

    echo "Waiting for Operator CSV labelled as $operator_label to be created..."
    while [[ $(oc get csv -n "$operator_namespace" -l "$operator_label" 2>/dev/null | wc -l) -le 1 ]]; do
        sleep 5
    done

    oc wait --for=jsonpath='{.status.phase}'=Succeeded csv -n "$operator_namespace" -l "$operator_label" --timeout=300s
}

echo "...OPENSHIFT LOGGING OPERATOR..."

# 1. Ensure the namespace exists (though your Loki script creates it, it's safer to have here too)
oc create namespace $LOGGING_NAMESPACE --dry-run=client -o yaml | oc apply -f -

# 2. Create the OperatorGroup for Logging
if check_openshift_resource_exists OperatorGroup cluster-logging-operator $LOGGING_NAMESPACE; then
  echo " - OperatorGroup already exists"
else
  cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: cluster-logging-operator
  namespace: $LOGGING_NAMESPACE
spec:
  targetNamespaces:
  - $LOGGING_NAMESPACE
EOF
fi

# 3. Create the Subscription
if check_openshift_resource_exists Subscription cluster-logging $LOGGING_NAMESPACE; then
  echo " - Logging Subscription already exists"
else
  echo " - Creating Logging Subscription"
  cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  labels:
    operators.coreos.com/cluster-logging.openshift-logging: ""
    observability-demo-framework: 'operator'
  name: cluster-logging
  namespace: $LOGGING_NAMESPACE
spec:
  channel: stable-6.5
  installPlanApproval: Automatic
  name: cluster-logging
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF
fi

# 4. Wait for installation
wait_operator_to_be_installed operators.coreos.com/cluster-logging.openshift-logging $LOGGING_NAMESPACE

echo " - OpenShift Logging Operator installation complete!"

echo "...CLUSTER LOG FORWARDER RESOURCE..."
cat <<EOF | oc apply -f - 
apiVersion: observability.openshift.io/v1
kind: ClusterLogForwarder
metadata:
  name: instance
  namespace: openshift-logging
spec:
  managementState: Managed
  serviceAccount:
    name: loki-collector
  filters: 
  - name: multiline
    type: detectMultilineException
  inputs:
    - name: user-apps-logs
      type: application
      application:
        includes:
          - namespace: "obs-demo-*"
  outputs:
    - name: loki-apps
      type: lokiStack
      lokiStack:
        # THE TARGET IS THE LOKISTACK CR ITSELF
        target:
          name: logging-loki        
          namespace: openshift-logging
        authentication:
          token:
            from: serviceAccount
      tls:
        ca:
          key: service-ca.crt
          configMapName: openshift-service-ca.crt
  pipelines:
    - name: filtered-apps-to-loki
      inputRefs:
        - user-apps-logs
      filterRefs: 
        - multiline
      outputRefs:
        - loki-apps
EOF

echo " - OpenShift ClusterLogForwarder created!"