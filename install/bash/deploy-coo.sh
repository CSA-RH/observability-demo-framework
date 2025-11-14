#!/bin/bash
set -e
source ./env.sh
# Deploy Cluster Observability Operator
echo ...CLUSTER OBSERVABILITY OPERATOR AND UI PLUGINS... 
#  - Operator installation 
cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  generation: 1
  labels:
    operators.coreos.com/cluster-observability-operator.openshift-operators: ""
    observability-demo-framework: 'operator'
  name: cluster-observability-operator
  namespace: openshift-operators
spec:
  channel: stable
  installPlanApproval: Automatic
  name: cluster-observability-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
  startingCSV: cluster-observability-operator.v1.2.2
EOF

wait_operator_to_be_installed operators.coreos.com/cluster-observability-operator.openshift-operators openshift-operators

#  - Operator plugins 
echo " - Install UI plugins"
cat <<EOF | oc apply -f -
apiVersion: observability.openshift.io/v1alpha1
kind: UIPlugin
metadata:
  name: distributed-tracing
  labels: 
    observability-demo-framework: 'ui'
spec:
  type: DistributedTracing
---
apiVersion: observability.openshift.io/v1alpha1
kind: UIPlugin
metadata:
  name: logging
  labels: 
    observability-demo-framework: 'ui'
spec:
  logging:
    lokiStack:
      name: loki
  type: Logging
EOF