# OpenTelemetry Collector Integration with Elastic Cloud (Serverless on AWS)

This guide provides a walkthrough on how to deploy and configure an OpenTelemetry (OTel) Collector to receive telemetry data (metrics, logs and traces) from your applications and export it to an Elastic Cloud Serverless project hosted on AWS.

## 📋 Prerequisites

Before starting, ensure you have the following ready:
* A working Kubernetes/OpenShift cluster.
* The **OpenTelemetry Operator** (e.g., Red Hat build of OpenTelemetry) installed on your cluster.
* Applications deployed in the cluster that are already instrumented to emit metrics, logs and traces in **OTLP format** (e.g., via the `Instrumentation` CRD).

---

## 🔑 Step 1: Obtain Elastic Cloud Credentials

To allow the OTel Collector to push data to Elastic, you need two pieces of information from your Elastic Cloud console: the **Ingest Endpoint** and an **API Key**.

### Finding the Ingest Endpoint
1. Log in to [cloud.elastic.co](https://cloud.elastic.co).
2. Locate your Serverless **Observability Project**.
3. Click the **Manage** button next to your project.
4. Look for the **Endpoints** section (or "Application endpoints, cluster and component IDs").
5. Copy the URL labeled **Ingest** or **Managed OTLP**. 
   * *Note: Ensure it is the Ingest/APM endpoint (typically contains `.ingest.` or `.apm.`), NOT the Elasticsearch database endpoint (which contains `.es.`).*

### Generating the API Key
1. In the same project management screen, navigate to the **API Keys** section.
2. Click **Create API Key**.
3. Give it a descriptive name (e.g., `otel-collector-exporter`).
4. Copy the generated Base64 API Key. **Save it securely**, as you will not be able to see it again.

![Create API key](create-api-key.png)

![Example of created API key](sample-api-key-created.png)

---

## 🚀 Step 2: Deploy the OTel Collector

The following script creates the required `ServiceAccount` and deploys the `OpenTelemetryCollector` custom resource. The collector is configured to receive OTLP data internally via gRPC/HTTP and export it using the robust `otlp_http` protocol to Elastic.

> **⚠️ Security Warning:** For demonstration and laboratory purposes, the API key is hardcoded in the `headers` section below. For production environments, you should store this key in a Kubernetes `Secret` and reference it in the collector configuration using environment variables.

Run the following commands in your terminal, replacing the placeholders with your actual Elastic data:

```bash
export CURRENT_NAMESPACE=obs-demo

# 1. Create the ServiceAccount
echo " - Creating Service Account"
cat <<EOF | oc apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:  
  name: otel-collector
  namespace: $CURRENT_NAMESPACE
EOF

# 2. Provide RBAC permissions for OTel to be able to scrape metrics from pods.
echo " - Providing RBAC to otel-collector Service Account"
cat <<EOF | oc apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: otel-collector-view
rules:
  - apiGroups: [""]
    resources:
      - nodes
      - nodes/proxy
      - services
      - endpoints
      - pods
    verbs: ["get", "list", "watch"]
  - apiGroups: ["extensions", "apps"]
    resources:
      - daemonsets
      - deployments
      - replicasets
      - statefulsets
    verbs: ["get", "list", "watch"]
  - nonResourceURLs: ["/metrics"]
    verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: otel-collector-view-binding
subjects:
  - kind: ServiceAccount
    name: otel-collector
    namespace: obs-demo 
roleRef:
  kind: ClusterRole
  name: otel-collector-view 
  apiGroup: rbac.authorization.k8s.io
EOF

# 3. Install the OTel Collector
echo " - Installing OTel Collector"
export ELASTIC_INGEST_ENDPOINT=<YOUR_INGEST_ENDPOINT>
export ELASTIC_API_KEY=<YOUR_API_KEY>
cat <<EOF | oc apply -f -  
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: otel
  namespace: $CURRENT_NAMESPACE
spec:
  observability:
    metrics:
      enableMetrics: true
  config:
    processors:
      batch: {}
      memory_limiter:
        check_interval: 1s
        limit_percentage: 75
        spike_limit_percentage: 15
    exporters:      
      otlp_http/elastic:
        # REPLACE with your Elastic Ingest/APM URL (ensure it starts with https://)
        endpoint: 'https://$ELASTIC_INGEST_ENDPOINT'
        tls:
          insecure: false
        headers:
          # REPLACE with your actual API Key
          Authorization: 'ApiKey $ELASTIC_API_KEY'          
    receivers:      
      prometheus:
        config:
          scrape_configs:
            - job_name: 'openshift-apps-scraping'              
              kubernetes_sd_configs:
                - role: pod              
              relabel_configs:                
                - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
                  action: keep
                  regex: true
                
                - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
                  action: replace
                  target_label: __metrics_path__
                  regex: (.+)
                
                - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
                  action: replace
                  regex: ([^:]+)(?::\d+)?;(\d+)
                  replacement: $1:$2
                  target_label: __address__
                
                - source_labels: [__meta_kubernetes_namespace]
                  action: replace
                  target_label: namespace
                - source_labels: [__meta_kubernetes_pod_name]
                  action: replace
                  target_label: pod            
      otlp:
        protocols:
          grpc:
            endpoint: '0.0.0.0:4317'
          http:
            endpoint: '0.0.0.0:4318'            
    service:
      pipelines:
        metrics:
          receivers:
            - prometheus
          processors:
            - memory_limiter
            - batch
          exporters:
            - otlp_http/elastic          
        logs:
          exporters:
            - otlp_http/elastic
          receivers:
            - otlp
        traces:
          exporters:
            - otlp_http/elastic
          receivers:
            - otlp            
  mode: deployment
  managementState: managed  
  serviceAccount: otel-collector
EOF
```

For pods in the target namespace, we need to annotate the pods with the specified filters for the collector being able to scrape the endpoint

```bash
oc get deploy -n $TARGET_NAMESPACE -oname \
  | xargs -I {} oc patch {} \
    -n $TARGET_NAMESPACE \
    -p '{"spec":{"template":{"metadata":{"annotations":{"prometheus.io/scrape":"true","prometheus.io/port":"8081","prometheus.io/path":"/metrics"}}}}}'
 
```

## 🧪 Step 3: Verification

Once the pod for the OpenTelemetry Collector is in a `Running` state, it will start receiving data from your apps and forwarding it.

To verify that the pipeline is working:

1. Open your Elastic Cloud project UI (Kibana).
   
2. For Metrics: Go to Discover -> Select APM -> write the metric name (`meloinvento` in the image), select one item and search for the metric name to see the value.

![Create a custom metric (with the app)](metrics-app.png)

![Inspect the value in Elastic](metrics-kibana.png)  

3. For Logs: Go to Discover or Observability -> Logs -> Stream. You should see your application logs flowing in.

4. For Traces: Go to Observability -> APM -> Services. You should see your instrumented application listed. Click on it to explore the transaction waterfalls and trace data.
