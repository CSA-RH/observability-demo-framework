#!/bin/bash
source ./env.sh

echo "...OPENSHIFT LOGGING OPERATOR..."

# 1. Ensure the namespace exists (though your Loki script creates it, it's safer to have here too)
oc create namespace $GLOBAL_LOGGING_NAMESPACE --dry-run=client -o yaml | oc apply -f -

# 2. Create the OperatorGroup for Logging
if check_openshift_resource_exists OperatorGroup cluster-logging-operator $GLOBAL_LOGGING_NAMESPACE; then
  echo " - OperatorGroup already exists"
else
  cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: cluster-logging-operator
  namespace: $GLOBAL_LOGGING_NAMESPACE
spec:
  targetNamespaces:
  - $GLOBAL_LOGGING_NAMESPACE
EOF
fi

# 3. Create the Subscription
if check_openshift_resource_exists Subscription cluster-logging $GLOBAL_LOGGING_NAMESPACE; then
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
  namespace: $GLOBAL_LOGGING_NAMESPACE
spec:
  channel: stable-6.5
  installPlanApproval: Automatic
  name: cluster-logging
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF
fi

# 4. Wait for installation
wait_operator_to_be_installed operators.coreos.com/cluster-logging.openshift-logging $GLOBAL_LOGGING_NAMESPACE

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
        target:
          name: $GLOBAL_LOKISTACK_RESOURCE
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