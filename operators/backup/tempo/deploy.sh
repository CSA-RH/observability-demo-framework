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
  managementState: Managed
  serviceAccount: tempo-escotilla
  template:
    queryFrontend:
      jaegerQuery:
        enabled: true
        ingress:
          type: route
  storage:
    secret:
      name: tempo-storage-secret
      type: azure
    tls:
      enabled: false
  storageSize: 5Gi
EOF

# Create OTel Collector
export CURRENT_NAMESPACE=$(oc project -q)
cat <<EOF | oc apply -f - 
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: otel
spec:
  serviceAccount: otel-collector
  config:
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: '0.0.0.0:4317'
          http:
            endpoint: '0.0.0.0:4318'
    exporters:
      otlp:        
        endpoint: 'tempo-escotilla-distributor:4317'
        tls:        
          insecure: true    
    service:
      pipelines:
        traces:
          receivers:
            - otlp
          exporters:
            - otlp
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





TESTING

# Create TempoStack resource
cat <<EOF | oc apply -f -
apiVersion: tempo.grafana.com/v1alpha1
kind: TempoStack
metadata:
  labels:
    observability-demo-framework: traces
  name: escotilla
spec:
  managementState: Managed
  serviceAccount: tempo-escotilla
  template:
    queryFrontend:
      jaegerQuery:
        enabled: true
        authentication: 
          enabled: false
        ingress:
          type: route
  storage:
    secret:
      name: tempo-storage-secret
      type: azure
    tls:
      enabled: false
  storageSize: 5Gi
EOF



#https://tempo-escotilla-query-frontend-obs-df-install-6.apps.sm4036i1c5ea0ae061.germanywestcentral.aroapp.io/api/traces?service=escotilla-nodejs-service

#Enable RED metrics
# Tempo configuration

# OTel configuration

# Service Monitor



