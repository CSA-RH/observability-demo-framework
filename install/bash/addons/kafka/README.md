# Connecting two collectors via Kafka topics for logs and metrics. 

## Install operators
- Streams for Kafka (For create cluster and topics to send/receive telemetry)
- Loki (storage backend for logs)
- Tempo (storage backend for traces)
- OpenTelemetry (operator for collector and auto instrumentation)
- Cluster Observability Operator (ui plugins for traces and logs UI)

## Create the Kakfa cluster and the topics

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: amq-streams
---
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: dual-role
  namespace: amq-streams
  labels:
    strimzi.io/cluster: telemetry-kafka
spec:
  replicas: 2
  roles:
    - controller
    - broker
  storage:
    type: ephemeral  # Change to persistent-claim if using persistent Ceph/ODF storage
---
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: telemetry-kafka
  namespace: amq-streams
  annotations:
    strimzi.io/node-pools: enabled
    strimzi.io/kraft: enabled
spec:
  kafka:
    version: 4.1.0
    metadataVersion: 4.1-IV0
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
    config:
      # Replication factors adapted for 2 nodes
      offsets.topic.replication.factor: 2
      transaction.state.log.replication.factor: 2
      # Allows single-node survival during updates/maintenance
      transaction.state.log.min.isr: 1
      default.replication.factor: 2
      min.insync.replicas: 1
  entityOperator:
    topicOperator: {}
    userOperator: {}
---
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: otlp-logs
  namespace: amq-streams
  labels:
    strimzi.io/cluster: telemetry-kafka
spec:
  partitions: 2
  replicas: 2
---
# Optional: keep trace and metric topics ready if also sending to Tempo and VictoriaMetrics
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: otlp-spans
  namespace: amq-streams
  labels:
    strimzi.io/cluster: telemetry-kafka
spec:
  partitions: 2
  replicas: 2
---
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: otlp-metrics
  namespace: amq-streams
  labels:
    strimzi.io/cluster: telemetry-kafka
spec:
  partitions: 2
  replicas: 2
```

## Create Object bucket claims for Tempo and Loki
Create 2-replicas node cluster because the test cluster I got has 2 nodes. Not the optimal solution due to quorum.

### For tempo

1. create the file `setup-tempo-storage.sh` with the following content

```bash
#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="obs-demo"
OBC_NAME="tempostack-storage"
TEMPO_SECRET_NAME="tempo-s3-secret"
S3_STORAGE_CLASS=openshift-storage.noobaa.io

echo "=== 1. Ensuring namespace ${NAMESPACE} exists ==="
oc get namespace "${NAMESPACE}" >/dev/null 2>&1 || oc create namespace "${NAMESPACE}"

echo "=== 2. Creating ObjectBucketClaim: ${OBC_NAME} ==="
cat <<EOF | oc apply -f -
apiVersion: objectbucket.io/v1alpha1
kind: ObjectBucketClaim
metadata:
  name: ${OBC_NAME}
  namespace: ${NAMESPACE}
spec:
  generateBucketName: tempostack-bucket
  storageClassName: $S3_STORAGE_CLASS
EOF

echo "=== 3. Waiting for ObjectBucketClaim ${OBC_NAME} to be Bound ==="
RETRIES=30
until [[ $(oc get obc "${OBC_NAME}" -n "${NAMESPACE}" -o jsonpath='{.status.phase}' 2>/dev/null || true) == "Bound" ]]; do
  RETRIES=$((RETRIES - 1))
  if [[ $RETRIES -le 0 ]]; then
    echo "ERROR: Timed out waiting for OBC ${OBC_NAME} to become Bound."
    exit 1
  fi
  echo "Waiting for bucket provisioning... (${RETRIES} retries remaining)"
  sleep 3
done
echo "OBC ${OBC_NAME} is Bound!"

echo "=== 4. Extracting bucket parameters and credentials ==="
BUCKET_NAME=$(oc get cm "${OBC_NAME}" -n "${NAMESPACE}" -o jsonpath='{.data.BUCKET_NAME}')
BUCKET_HOST=$(oc get cm "${OBC_NAME}" -n "${NAMESPACE}" -o jsonpath='{.data.BUCKET_HOST}')
AWS_ACCESS_KEY_ID=$(oc get secret "${OBC_NAME}" -n "${NAMESPACE}" -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)
AWS_SECRET_ACCESS_KEY=$(oc get secret "${OBC_NAME}" -n "${NAMESPACE}" -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 -d)

# For internal ODF (s3.openshift-storage.svc), we use http:// on port 80 to avoid CA trust issues
if [[ "${BUCKET_HOST}" == "s3.openshift-storage.svc" ]]; then
  ENDPOINT="http://s3.openshift-storage.svc:80"
else
  ENDPOINT="http://${BUCKET_HOST}:80"
fi

echo "Discovered Bucket Name : ${BUCKET_NAME}"
echo "Configuring Endpoint   : ${ENDPOINT}"

echo "=== 5. Creating TempoStack S3 Secret: ${TEMPO_SECRET_NAME} ==="
# Delete existing secret if it exists to ensure a clean state
oc delete secret "${TEMPO_SECRET_NAME}" -n "${NAMESPACE}" --ignore-not-found=true

oc create secret generic "${TEMPO_SECRET_NAME}" -n "${NAMESPACE}" \
  --from-literal=bucket="${BUCKET_NAME}" \
  --from-literal=endpoint="${ENDPOINT}" \
  --from-literal=access_key_id="${AWS_ACCESS_KEY_ID}" \
  --from-literal=access_key_secret="${AWS_SECRET_ACCESS_KEY}" \
  --from-literal=insecure="true"

echo "=== Success! ==="
echo "Secret '${TEMPO_SECRET_NAME}' is ready in namespace '${NAMESPACE}'."
```

2. Make it executable: 

```bash
chmod +x setup-tempo-storage.sh
```

3. Execute the script: 

```bash
./setup-tempo-storage.sh
```

### For Loki 

1. Create the script `setup-loki-storage.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="openshift-logging"
OBC_NAME="lokistack-storage"
LOKI_SECRET_NAME="loki-s3-secret"
S3_STORAGE_CLASS=openshift-storage.noobaa.io

echo "=== 1. Ensuring namespace ${NAMESPACE} exists ==="
oc get namespace "${NAMESPACE}" >/dev/null 2>&1 || oc create namespace "${NAMESPACE}"

echo "=== 2. Creating ObjectBucketClaim: ${OBC_NAME} in ${NAMESPACE} ==="
cat <<EOF | oc apply -f -
apiVersion: objectbucket.io/v1alpha1
kind: ObjectBucketClaim
metadata:
  name: ${OBC_NAME}
  namespace: ${NAMESPACE}
spec:
  generateBucketName: lokistack-bucket  
  storageClassName: $S3_STORAGE_CLASS
EOF

echo "=== 3. Waiting for ObjectBucketClaim ${OBC_NAME} to be Bound ==="
RETRIES=30
until [[ $(oc get obc "${OBC_NAME}" -n "${NAMESPACE}" -o jsonpath='{.status.phase}' 2>/dev/null || true) == "Bound" ]]; do
  RETRIES=$((RETRIES - 1))
  if [[ $RETRIES -le 0 ]]; then
    echo "ERROR: Timed out waiting for OBC ${OBC_NAME} to become Bound."
    exit 1
  fi
  echo "Waiting for bucket provisioning... (${RETRIES} retries remaining)"
  sleep 3
done
echo "OBC ${OBC_NAME} is Bound!"

echo "=== 4. Extracting bucket parameters and credentials ==="
BUCKET_NAME=$(oc get cm "${OBC_NAME}" -n "${NAMESPACE}" -o jsonpath='{.data.BUCKET_NAME}')
BUCKET_HOST=$(oc get cm "${OBC_NAME}" -n "${NAMESPACE}" -o jsonpath='{.data.BUCKET_HOST}')
AWS_ACCESS_KEY_ID=$(oc get secret "${OBC_NAME}" -n "${NAMESPACE}" -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)
AWS_SECRET_ACCESS_KEY=$(oc get secret "${OBC_NAME}" -n "${NAMESPACE}" -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 -d)

# For internal ODF (s3.openshift-storage.svc), route via port 80 to bypass internal TLS CA verification
if [[ "${BUCKET_HOST}" == "s3.openshift-storage.svc" ]]; then
  ENDPOINT="http://s3.openshift-storage.svc:80"
else
  ENDPOINT="http://${BUCKET_HOST}:80"
fi

echo "Discovered Bucket Name : ${BUCKET_NAME}"
echo "Configuring Endpoint   : ${ENDPOINT}"

echo "=== 5. Creating LokiStack S3 Secret: ${LOKI_SECRET_NAME} ==="
# Delete existing secret if it exists to ensure a clean state
oc delete secret "${LOKI_SECRET_NAME}" -n "${NAMESPACE}" --ignore-not-found=true

# Note: Loki Operator expects 'bucketnames' (plural)
oc create secret generic "${LOKI_SECRET_NAME}" -n "${NAMESPACE}" \
  --from-literal=bucketnames="${BUCKET_NAME}" \
  --from-literal=endpoint="${ENDPOINT}" \
  --from-literal=access_key_id="${AWS_ACCESS_KEY_ID}" \
  --from-literal=access_key_secret="${AWS_SECRET_ACCESS_KEY}" \
  --from-literal=insecure="true" \
  --from-literal=insecure_skip_verify="true"

echo "=== Success! ==="
echo "Secret '${LOKI_SECRET_NAME}' is ready in namespace '${NAMESPACE}'."
```

2. Make it executable: 

```bash
chmod +x setup-loki-storage.sh
```

3. Execute the script: 

```bash
./setup-loki-storage.sh
```

## Create Tempo stack resource 

```yaml
kind: ServiceAccount
apiVersion: v1
metadata:
  name: tempo-escotilla
  namespace: obs-demo
---
apiVersion: tempo.grafana.com/v1alpha1
kind: TempoStack
metadata:
  name: escotilla
  namespace: obs-demo
  labels:
    app.kubernetes.io/managed-by: tempo-operator
    observability-demo-framework: traces
spec:
  tenants:
    authentication:
      - tenantId: obsdemo
        tenantName: obsdemo
    mode: openshift
  serviceAccount: tempo-escotilla  
    queryFrontend:
      jaegerQuery:
        enabled: true
  storage:
    secret:
      name: tempo-s3-secret
      type: s3
    tls:
      enabled: false  
```

## Create Loki stack resource

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-logging
---
apiVersion: loki.grafana.com/v1
kind: LokiStack
metadata:
  name: loki
  namespace: openshift-logging
spec:
  hashRing:
    type: memberlist
  limits:
    global:
      queries:
        queryTimeout: 3m
  managementState: Managed
  size: 1x.demo
  storage:
    schemas:
      - effectiveDate: '2022-06-01'
        version: v12
      - effectiveDate: '2024-04-02'
        version: v13
    secret:
      name: loki-s3-secret
      type: s3
  storageClassName: ocs-external-storagecluster-ceph-rbd
  tenants:
    mode: openshift-logging
```

## Create the collector for app logs and traces (possibly expand to metrics as well)


```yaml
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: otel
  namespace: obs-demo
spec:
  config:
    exporters:
      kafka:
        brokers:
          - 'telemetry-kafka-kafka-bootstrap.amq-streams.svc:9092'
        logs:
          topic: otlp-logs
        metrics:
          topic: otlp-metrics
        protocol_version: 2.0.0
        traces:
          topic: otlp-spans
    processors:
      batch:
        send_batch_size: 8192
        timeout: 1s
      k8sattributes:
        auth_type: serviceAccount
        passthrough: false
      memory_limiter:
        check_interval: 1s
        limit_percentage: 65
        spike_limit_percentage: 20
      resource:
        attributes:
          - action: upsert
            from_attribute: k8s.namespace.name
            key: kubernetes.namespace_name
          - action: upsert
            from_attribute: k8s.pod.name
            key: kubernetes.pod_name
          - action: upsert
            from_attribute: k8s.container.name
            key: kubernetes.container_name
          - action: upsert
            key: log_type
            value: application
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
      pipelines:
        logs:
          exporters:
            - kafka
          processors:
            - memory_limiter
            - k8sattributes
            - transform
            - resource
            - batch
          receivers:
            - otlp
        metrics:
          exporters:
            - kafka
          processors:
            - memory_limiter
            - batch
          receivers:
            - otlp
        traces:
          exporters:
            - kafka
          processors:
            - memory_limiter
            - batch
          receivers:
            - otlp
      telemetry:
        metrics:
          readers:
            - pull:
                exporter:
                  prometheus:
                    host: 0.0.0.0
                    port: 8888
  managementState: managed
  serviceAccount: otel-collector
  replicas: 1  
```

## Create the target collector to kafka topics
```yaml
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: tempo-traces-writer-obsdemo
rules:
  - apiGroups:
      - tempo.grafana.com
    resources:
      - obsdemo
      - traces
      - '*'
    verbs:
      - create
      - get
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: tempo-traces-writer-obsdemo-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: tempo-traces-writer-obsdemo
subjects:
  - kind: ServiceAccount
    name: otel-collector-target
    namespace: obs-demo-collector
---
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: otel-collector-target-logs-writer
rules:
  - apiGroups:
      - loki.grafana.com
    resources:
      - application
    resourceNames:
      - logs
    verbs:
      - create
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: otel-collector-target-logs-writer-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: otel-collector-target-logs-writer
subjects:
  - kind: ServiceAccount
    name: otel-collector-target
    namespace: obs-demo-collector
---
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: otel-target
  namespace: obs-demo-collector
spec:
  deploymentUpdateStrategy: {}
  config:
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
      batch:
        send_batch_size: 8192
        timeout: 1s
      memory_limiter:
        check_interval: 1s
        limit_percentage: 65
        spike_limit_percentage: 20
    receivers:
      kafka/logs:
        brokers:
          - 'telemetry-kafka-kafka-bootstrap.amq-streams.svc:9092'
        group_id: otel-target-logs
        logs:
          topics:
            - otlp-logs
        protocol_version: 2.0.0
      kafka/spans:
        brokers:
          - 'telemetry-kafka-kafka-bootstrap.amq-streams.svc:9092'
        group_id: otel-target-spans
        protocol_version: 2.0.0
        traces:
          topics:
            - otlp-spans
    service:
      extensions:
        - bearertokenauth
      pipelines:
        logs:
          exporters:
            - otlphttp/loki
          processors:
            - memory_limiter
            - batch
          receivers:
            - kafka/logs
        traces:
          exporters:
            - otlp/tempo
          processors:
            - memory_limiter
            - batch
          receivers:
            - kafka/spans
  mode: deployment
  serviceAccount: otel-collector-target
  replicas: 1
```