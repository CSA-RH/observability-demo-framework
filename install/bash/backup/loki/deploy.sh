export CURRENT_NAMESPACE=$(oc project -q)

# Define variables
STORAGE_ACCOUNT_NAME="obsdemopalma"
RESOURCE_GROUP="aro-palma"
LOCATION="germanywestcentral"
CONTAINER_NAME="lokistack-container"

# Export random number for later use
export RANDOM_NUMBER

# Create the storage account with a tag
az storage account create \
  --name $STORAGE_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --tags observability-demo-framework=storage

# Retrieve the storage account key (key 1) and export it as an environment variable
ACCOUNT_KEY=$(az storage account keys list \
  --resource-group $RESOURCE_GROUP \
  --account-name $STORAGE_ACCOUNT_NAME \
  --query "[0].value" -o tsv)

oc create secret generic logging-loki-azure \
  --from-literal=container=$CONTAINER_NAME \
  --from-literal=environment=AzureGlobal \
  --from-literal=account_name=$STORAGE_ACCOUNT_NAME \
  --from-literal=account_key=$ACCOUNT_KEY


# Information: 
#  https://docs.redhat.com/en/documentation/openshift_container_platform/4.17/html-single/logging/index#log6x-input-spec-filter-namespace-container_logging-6x-6.1
#  https://docs.openshift.com/container-platform/4.17/observability/logging/logging-6.1/log6x-release-notes-6.1.html


export LOKISTACK_RESOURCE=loki
cat <<EOF | oc apply -f -
apiVersion: loki.grafana.com/v1
kind: LokiStack
metadata:
  name: $LOKISTACK_RESOURCE
  namespace: openshift-logging
spec:
  tenants:
    mode: openshift-logging
  managementState: Managed
  limits:
    global:
      queries:
        queryTimeout: 3m
  storage:
    schemas:
      - effectiveDate: '2022-06-01'
        version: v12
      - effectiveDate: "2024-04-02"
        version: v13
    secret:
      name: logging-loki-azure
      type: azure
  hashRing:
    type: memberlist
  size: 1x.demo
  storageClassName: managed-csi
EOF

# Create Service Account for loki collector
export SA_COLLECTOR=loki-collector
cat <<EOF | oc apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: $SA_COLLECTOR
  namespace: openshift-logging
EOF

# Grant permissions to the service account
cat <<EOF | oc apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: logging-collector-logs-writer
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: logging-collector-logs-writer
subjects:
- kind: ServiceAccount
  name: $SA_COLLECTOR
  namespace: openshift-logging
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:  
  name: collect-application-logs
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: collect-application-logs
subjects:
- kind: ServiceAccount
  name: $SA_COLLECTOR
  namespace: openshift-logging
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: collect-audit-logs
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: collect-audit-logs
subjects:
- kind: ServiceAccount
  name: $SA_COLLECTOR
  namespace: openshift-logging
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: collect-infrastructure-logs
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: collect-infrastructure-logs
subjects:
- kind: ServiceAccount
  name: $SA_COLLECTOR
  namespace: openshift-logging
EOF

# Create UI pluging for logging
cat <<EOF | oc apply -f -
apiVersion: observability.openshift.io/v1alpha1
kind: UIPlugin
metadata:
  name: logging
spec:
  type: Logging
  logging:
    lokiStack:
      name: $SA_COLLECTOR
EOF

# Create ClusterLogForwarder (OPTION 1)
cat <<EOF | oc apply -f -
apiVersion: observability.openshift.io/v1
kind: ClusterLogForwarder
metadata:
  name: collector
  namespace: openshift-logging
spec:
  serviceAccount: 
    name: $SA_COLLECTOR
  filters:
  - name: multiline-exception
    type: detectMultilineException
  inputs: 
  - name: escotilla-app
    application: 
      includes: 
      - namespace: $CURRENT_NAMESPACE    
    type: application    
  outputs:
  - name: default-lokistack
    type: lokiStack
    lokiStack:
      authentication:
        token:
          from: serviceAccount
      target:
        name: $LOKISTACK_RESOURCE
        namespace: openshift-logging
    tls:
      ca:
        key: service-ca.crt
        configMapName: openshift-service-ca.crt
  pipelines:
  - name: default-logstore
    filterRefs: 
    - multiline-exception
    inputRefs:
    - escotilla-app
    outputRefs:
    - default-lokistack
EOF

# Adapt OTel Collector to forward logs from OpenTelemetry (OPTION 2)
# Link: https://docs.openshift.com/container-platform/4.17/observability/otel/otel-forwarding-telemetry-data.html#otel-forwarding-logs-to-tempostack_otel-forwarding-telemetry-data

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

cat <<EOF | oc apply -f -
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: otel  
spec:
  serviceAccount: otel-collector
  config:
    connectors:
      spanmetrics: 
        metrics_flush_interval: 15s
    extensions:
      bearertokenauth:
        filename: "/var/run/secrets/kubernetes.io/serviceaccount/token"
    receivers:
      otlp:
        protocols:
          grpc: {}
          http: {}
    processors:
      k8sattributes:
        auth_type: "serviceAccount"
        passthrough: false
        extract:
          metadata:
            - k8s.pod.name
            - k8s.container.name
            - k8s.namespace.name
          labels:
          - tag_name: app.label.component
            key: app.kubernetes.io/component
            from: pod
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
          - key: loki.format 
            action: insert
            value: json
          - key:  kubernetes_namespace_name
            from_attribute: k8s.namespace.name
            action: upsert
          - key:  kubernetes_pod_name
            from_attribute: k8s.pod.name
            action: upsert
          - key: kubernetes_container_name
            from_attribute: k8s.container.name
            action: upsert
          - key: log_type
            value: application
            action: upsert
          - key: loki.resource.labels 
            value: log_type, kubernetes_namespace_name, kubernetes_pod_name, kubernetes_container_name
            action: insert
      transform:
        log_statements:
          - context: log
            statements:
              - set(attributes["level"], ConvertCase(severity_text, "lower"))
    exporters:
      loki:
        endpoint: https://loki-gateway-http.openshift-logging.svc.cluster.local:8080/api/logs/v1/application/loki/api/v1/push 
        tls:
          ca_file: "/var/run/secrets/kubernetes.io/serviceaccount/service-ca.crt"
        auth:
          authenticator: bearertokenauth
      debug:
        verbosity: detailed
      otlp:        
        endpoint: 'tempo-escotilla-distributor:4317'
        tls:        
          insecure: true      
      prometheus: 
        endpoint: 0.0.0.0:8889
        add_metric_suffixes: false
        resource_to_telemetry_conversion:
          enabled: true
    service:
      extensions: [bearertokenauth] 
      pipelines:
        metrics:           
          receivers: [spanmetrics]
          exporters: [prometheus]
        traces:          
          receivers: [otlp]            
          exporters: [otlp, spanmetrics]            
        logs:
          receivers: [otlp]
          processors: [k8sattributes, transform, resource]
          exporters: [loki] 
        logs/test:
          receivers: [otlp]
          processors: []
          exporters: [debug]
EOF

# TEST logging
#   write
ADDRESS=https://loki-gateway-http.openshift-logging.svc.cluster.local:8080/api/logs/v1/application/loki/api/v1/push 
curl -X POST -k \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "streams": [
      {
        "stream": {
          "job": "test-job",
          "level": "info"
        },
        "values": [
          ["'$(date +%s%N)'", "This is a test log entry"]
        ]
      }
    ]
  }' \
  $ADDRESS

#   read
curl -X GET -k \
  -H "Authorization: Bearer $TOKEN" \
  -G \
  --data-urlencode 'query={job="test-job"}' \
  --data-urlencode 'limit=10' \
  $ADDRESS
