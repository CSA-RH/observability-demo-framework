#!/bin/bash
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
  installPlanApproval: Manual
  name: opentelemetry-product
  source: redhat-operators
  sourceNamespace: openshift-marketplace
  startingCSV: opentelemetry-operator.v0.113.0-2
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
  namespace: $GLOBAL_ROOT_NAMESPACE
EOF

#  - Collector
echo " - Install OTel Collector"
cat <<EOF | oc apply -f -  
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: otel
  namespace: $GLOBAL_ROOT_NAMESPACE
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
      otlp/obsdemo:
        auth:
          authenticator: bearertokenauth
        endpoint: 'tempo-escotilla-gateway.$GLOBAL_ROOT_NAMESPACE.svc.cluster.local:8090'
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
  namespace: $GLOBAL_ROOT_NAMESPACE
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