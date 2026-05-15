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