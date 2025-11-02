# Get storage account

# Create secret

# Create TempoStack resource
cat <<EOF | oc apply -f -
apiVersion: tempo.grafana.com/v1alpha1
kind: TempoStack
metadata:
  labels:
    observability-demo-framework: traces
  name: escotilla
spec:
  tenants:
    authentication:
      - tenantId: 63b7a8fc-db36-11ef-9036-047bcb601b1b   # For instance
        tenantName: obsdemo
    mode: openshift
  managementState: Managed
  serviceAccount: tempo-escotilla
  template:
    gateway:
      enabled: true
      ingress:
        route:
          termination: reencrypt
        type: route
    queryFrontend:
      jaegerQuery:
        enabled: true
        monitorTab:
          enabled: false
          prometheusEndpoint: ''
  storage:
    secret:
      name: tempo-storage-secret
      type: azure
    tls:
      enabled: false
  storageSize: 5Gi
EOF

# Create RBAC and permissions to enable authenticated calls
cat <<EOF | oc apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: tempostack-traces-reader
  labels: 
    observability-demo-framework: rbac
rules:
- apiGroups:
  - tempo.grafana.com
  resourceNames:
  - traces
  resources:
  - '*'
  verbs:
  - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: tempostack-traces-reader
  labels:
    observability-demo-framework: rbac
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: tempostack-traces-reader
subjects:
- apiGroup: rbac.authorization.k8s.io
  kind: Group
  name: system:authenticated
EOF

cat <<EOF | oc apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: tempostack-traces-write  
  labels: 
    observability-demo-framework: rbac
rules:
- apiGroups:
  - tempo.grafana.com
  resourceNames:
  - traces
  resources:
  - obsdemo
  verbs:
  - create
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: tempostack-traces
  labels: 
    observability-demo-framework: rbac
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: tempostack-traces-write
subjects:
- kind: ServiceAccount
  name: otel-collector
  namespace: $CURRENT_NAMESPACE
EOF

# Create OTel Collector
export CURRENT_NAMESPACE=$(oc project -q)
cat <<EOF | oc apply -f - 
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: otel
spec:
  config:
    exporters:
      otlp/obsdemo:
        auth:
          authenticator: bearertokenauth
        endpoint: 'tempo-escotilla-gateway.$CURRENT_NAMESPACE.svc.cluster.local:8090'
        headers:
          X-Scope-OrgID: obsdemo
        tls:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/service-ca.crt
          insecure: false
      otlphttp/obsdemo:
        auth:
          uthenticator: bearertokenauth
        endpoint: 'tempo-escotilla-gateway.$CURRENT_NAMESPACE.svc.cluster.local:8080/api/traces/v1/obsdemo'
        headers:
          X-Scope-OrgID: obsdemo
        tls:
          ca_file: /var/run/secrets/kubernetes.io/serviceaccount/service-ca.crt
          insecure: false
    extensions:
      bearertokenauth:
        filename: /var/run/secrets/kubernetes.io/serviceaccount/token
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
        traces:
          exporters:
            - otlp/obsdemo
          receivers:
            - otlp
      telemetry:
        metrics:
          address: '0.0.0.0:8888'
  mode: deployment
  managementState: managed
  serviceAccount: otel-collector
EOF

# Create Autoinstrumentation
cat <<EOF | oc apply -f -
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: demo-instrumentation
spec:
  exporter:
    endpoint: 'http://otel-collector:4317'
  java:
    image: 'ghcr.io/open-telemetry/opentelemetry-operator/autoinstrumentation-java:1.33.5'
  go:
  nodejs:
    env:
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: 'http://otel-collector:4317'  
  python:
    env:
      - name: OTEL_EXPORTER_OTLP_ENDPOINT
        value: 'http://otel-collector:4317'
EOF

# Create console plugin
cat <<EOF | oc apply -f -
apiVersion: observability.openshift.io/v1alpha1
kind: UIPlugin
metadata:
  name: distributed-tracing
spec:
  type: DistributedTracing
EOF