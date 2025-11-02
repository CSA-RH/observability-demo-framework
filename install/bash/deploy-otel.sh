# Load environment
source ./env.sh
# Deploy Red Hat build of OpenTelemetry Operator
echo ...RED HAT BUILD OF OPENTELEMETRY OPERATOR, COLLECTOR AND AUTO-INSTRUMENTATION... 
#  - Operator installation 
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-opentelemetry-operator
spec: {}
EOF
if check_openshift_resource_exists Subscription opentelemetry-product openshift-opentelemetry-operator; then
  echo " - OpenTelemetry Operator already installed"
else
  cat <<EOF | oc create -f -
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  annotations:
    olm.providedAPIs: Instrumentation.v1alpha1.opentelemetry.io,OpAMPBridge.v1alpha1.opentelemetry.io,OpenTelemetryCollector.v1alpha1.opentelemetry.io,OpenTelemetryCollector.v1beta1.opentelemetry.io
  generateName: openshift-opentelemetry-operator-
  namespace: openshift-opentelemetry-operator
  labels:
    observability-demo-framework: 'operator'
spec:
  upgradeStrategy: Default
EOF
  cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  labels:
    operators.coreos.com/opentelemetry-product.openshift-opentelemetry-operator: ""
    observability-demo-framework: 'operator'
  name: opentelemetry-product
  namespace: openshift-opentelemetry-operator    
spec:
  channel: stable
  installPlanApproval: Automatic
  name: opentelemetry-product
  source: redhat-operators
  sourceNamespace: openshift-marketplace
  startingCSV: opentelemetry-operator.v0.135.0-1
EOF
  # Wait for the operator to be created and available. 
  wait_operator_to_be_installed operators.coreos.com/opentelemetry-product.openshift-opentelemetry-operator openshift-opentelemetry-operator
fi

#   RBAC permissions
cat <<EOF | oc apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:  
  name: otel-collector
  namespace: $CURRENT_NAMESPACE
EOF
echo " - RBAC for OpenTelemetry"
cat <<EOF | oc apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: otel-collector-logs-writer
  labels:
    observability-demo-framework: rbac
rules:
 - apiGroups: ["loki.grafana.com"]
   resourceNames: ["logs"]
   resources: ["application"]
   verbs: ["create"]
 - apiGroups: [""]
   resources: ["pods", "namespaces", "nodes"]
   verbs: ["get", "watch", "list"]
 - apiGroups: ["apps"]
   resources: ["replicasets"]
   verbs: ["get", "list", "watch"]
 - apiGroups: ["extensions"]
   resources: ["replicasets"]
   verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: otel-collector-logs-writer
  labels:
    observability-demo-framework: rbac
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: otel-collector-logs-writer
subjects:
  - kind: ServiceAccount
    name: otel-collector
    namespace: $CURRENT_NAMESPACE
EOF

#  - Collector
echo " - Install OTel Collector"
cat <<EOF | oc apply -f -  
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: otel
  namespace: $CURRENT_NAMESPACE
  labels: 
    observability-demo-framework: 'otel'
spec:
  observability:
    metrics:
      enableMetrics: true
  config:
    connectors:
      spanmetrics:
        metrics_flush_interval: 15s
    exporters:      
      otlphttp:
        auth:
          authenticator: bearertokenauth
        endpoint: 'https://loki-gateway-http.openshift-logging.svc.cluster.local:8080/api/logs/v1/application/loki/api/v1/push'
        tls:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/service-ca.crt      
      otlp/obsdemo:
        auth:
          authenticator: bearertokenauth
        endpoint: 'tempo-escotilla-gateway.$CURRENT_NAMESPACE.svc.cluster.local:8090'
        headers:
          X-Scope-OrgID: obsdemo
        tls:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/service-ca.crt
          insecure: false
      prometheus:
        add_metric_suffixes: false
        endpoint: '0.0.0.0:8889'
        resource_to_telemetry_conversion:
          enabled: true
    extensions:
      bearertokenauth:
        filename: /var/run/secrets/kubernetes.io/serviceaccount/token
    processors:
      k8sattributes:
        auth_type: serviceAccount
        extract:
          labels:
            - from: pod
              key: app.kubernetes.io/component
              tag_name: app.label.component
          metadata:
            - k8s.pod.name
            - k8s.container.name
            - k8s.namespace.name
        passthrough: false
        pod_association:
          - sources:
              - from: resource_attribute
                name: k8s.pod.name
              - from: resource_attribute
                name: k8s.container.name
              - from: resource_attribute
                name: k8s.namespace.name
          - sources:
              - from: connection
      resource:
        attributes:
          - action: insert
            key: loki.format
            value: json
          - action: upsert
            from_attribute: k8s.namespace.name
            key: kubernetes_namespace_name
          - action: upsert
            from_attribute: k8s.pod.name
            key: kubernetes_pod_name
          - action: upsert
            from_attribute: k8s.container.name
            key: kubernetes_container_name
          - action: upsert
            key: log_type
            value: application
          - action: insert
            key: loki.resource.labels
            value: 'log_type, kubernetes_namespace_name, kubernetes_pod_name, kubernetes_container_name'
      transform:
        log_statements:
          - context: log
            statements:
              - 'set(attributes["level"], ConvertCase(severity_text, "lower"))'
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: '0.0.0.0:4317'
          http:
            endpoint: '0.0.0.0:4318'
    service:
      extensions:
        - bearertokenauth
      pipelines:
        logs:
          exporters:
            - otlphttp
          processors:
            - k8sattributes
            - transform
            - resource
          receivers:
            - otlp
        metrics:
          exporters:
            - prometheus
          receivers:
            - spanmetrics
        traces:
          exporters:
            - otlp/obsdemo
            - spanmetrics
          receivers:
            - otlp
  mode: deployment
  managementState: managed  
  serviceAccount: otel-collector
EOF

echo "   waiting for OTel Collector to initialize..."
sleep 2
oc wait \
    --for=condition=available \
    --timeout=300s \
    deployment otel-collector