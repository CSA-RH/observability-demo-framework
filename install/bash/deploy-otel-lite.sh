# Load environment
source ./env.sh
# Deploy Red Hat build of OpenTelemetry Operator
echo ...RED HAT BUILD OF OPENTELEMETRY OPERATOR, COLLECTOR AND AUTO-INSTRUMENTATION... 
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
      otlp/tempo:
        auth:
          authenticator: bearertokenauth
        endpoint: 'tempo-escotilla-gateway.obs-demo.svc.cluster.local:8090'
        headers:
          X-Scope-OrgID: obsdemo
        tls:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/service-ca.crt
      otlphttp/loki:
        auth:
          authenticator: bearertokenauth
        encoding: json
        endpoint: 'https://loki-gateway-http.openshift-logging.svc.cluster.local:8080/api/logs/v1/application/otlp'
        tls:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/service-ca.crt
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
            - otlphttp/loki
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
      telemetry:
        metrics:
          address: '0.0.0.0:8888'
  mode: deployment
  managementState: managed  
  serviceAccount: otel-collector
EOF

echo " - Install Auto instrumentation"
cat <<EOF | oc apply -f -
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: instrumentation
  namespace: $CURRENT_NAMESPACE
  labels:
    observability-demo-framework: 'otel'
spec:
  exporter:
    endpoint: 'http://otel-collector:4317'
  dotnet:
    env:
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: 'http://otel-collector:4318'
      - name: ASPNETCORE_HOSTINGSTARTUPASSEMBLIES
        value: OpenTelemetry.AutoInstrumentation.AspNetCoreBootstrapper
  nodejs:    
    env:
      - name: OTEL_NODEJS_AUTO_INSTRUMENTATION_ENABLED
        value: 'true'
      - name: OTEL_EXPORTER_OTLP_LOGS_ENDPOINT
        value: 'http://otel-collector:4318/v1/logs'
  propagators:
    - tracecontext
    - baggage
  sampler: {}
EOF
echo "   waiting for OTel Collector to initialize..."
oc wait \
    --for=condition=available \
    --timeout=300s \
    deployment otel-collector