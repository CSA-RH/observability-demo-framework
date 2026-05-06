This guide provides a comprehensive walkthrough for deploying the Prometheus Blackbox Exporter on OpenShift. This tool allows you to monitor endpoints (HTTP, HTTPS, ICMP, TCP) from the outside, ensuring your services are not just "running," but actually reachable and healthy.

# 1. Prepare the environment

First, we need to add the official Prometheus community repository to Helm. This ensures you are pulling the most stable and up-to-date version of the exporter.

```bash
# Register the Prometheus community helm chart repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

# Sync the local cache with the remote repository to see new versions
helm repo update
```

# 2. Deploy the Exporter

In OpenShift, it is a best practice to isolate monitoring tools. We will create a dedicated Namespace and then deploy the exporter using a values.yaml file to customize the configuration (such as defining modules like HTTP or ICMP).

```bash
# Create the namespace using a 'here-document' to pass the YAML directly to oc
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Namespace
metadata: 
  name: blackbox-exporter
spec: {}
EOF

# Install the exporter via Helm into the newly created namespace
# Note: Ensure blackbox-helm-values.yaml exists with your specific module configs
#.      (A copy of blackbox-helm-values.yaml is available in the same folder where 
#        this README document is located)
helm install blackbox prometheus-community/prometheus-blackbox-exporter \
  -n blackbox-exporter \
  -f blackbox-helm-values.yaml
```

# 3. Configure Probes (Synthetic Monitoring)

The `Probe` custom resource tells the Prometheus Operator which external or internal endpoints to check. Below, we define three probes: two for external Google services and one for a local internal service.

Note: The `prober.url` points to the internal Kubernetes DNS for the Blackbox service we just installed.

```yaml
---
apiVersion: monitoring.coreos.com/v1
kind: Probe
metadata:
  name: probe-google-http
  namespace: blackbox-exporter
spec:
  module: http_2xx 
  prober:
    url: blackbox-prometheus-blackbox-exporter.blackbox-exporter.svc.cluster.local:9115
  targets:
    staticConfig:
      static:
        - https://www.google.com
---
apiVersion: monitoring.coreos.com/v1
kind: Probe
metadata:
  name: probe-google-icmp
  namespace: blackbox-exporter
spec:
  module: icmp_ipv4
  prober:
    url: blackbox-prometheus-blackbox-exporter.blackbox-exporter.svc.cluster.local:9115
  targets:
    staticConfig:
      static:
        - www.google.com
---
apiVersion: monitoring.coreos.com/v1
kind: Probe
metadata:
  name: probe-hello-http
  namespace: blackbox-exporter
spec:
  module: http_2xx
  prober:
    url: blackbox-prometheus-blackbox-exporter.blackbox-exporter.svc.cluster.local:9115
  targets:
    staticConfig:
      static:
        - http://hello.sample.svc.cluster.local:8080
```

# 4. Define Alerting Rules

To make the monitoring actionable, we define a `PrometheusRule`. This rule monitors the `probe_success` metric. If the value is **0**, the check has failed.

```yaml
# alert-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: blackbox-alerts
  namespace: blackbox-exporter
spec:
  groups:
    - name: blackbox.rules
      rules:
        - alert: EndpointHelloDown
          expr: probe_success == 0 
          for: 1m
          labels:
            severity: critical
          annotations:
            summary: "The target {{ $labels.target }} is not responding."
            description: "The check of type {{ $labels.module }} executed from the custom blackbox exporter is not respoding since more than one minute."
```

# 5. Testing the Alert (Chaos Engineering)

To verify that your monitoring works, you must simulate a failure. Here is how you can trigger the EndpointHelloDown alert:

To create the app 
```bash
# Create namespace
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: sample
EOF

# Create deployment
cat <<EOF | oc apply -f - 
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    app: hello
  name: hello
  namespace: sample
spec:
  selector:
    matchLabels:
      app: hello
  template:
    metadata:
      labels:
        app: hello
    spec:
      containers:
      - image: openshift/hello-openshift
        name: hello-openshift
EOF

# Create service
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Service
metadata:
  labels:
    app: hello
  name: hello
  namespace: sample
spec:
  ports:
  - port: 8080
    protocol: TCP
    targetPort: 8080
  selector:
    app: hello
EOF
```

## Step A: Break the Application

Delete the service or scale the deployment to zero for your "hello" application.

```bash
# Delete the service to break networking to the pod
oc delete svc hello -n sample
# OR: Scale the application down
oc scale deployment hello --replicas=0 -n sample
```

## Step B: Observe the Flow

1. **Exporter Failure**: The Blackbox exporter attempts to hit the URL, fails, and sets `probe_success == 0`.
2. **Pending State**: In the OpenShift Monitoring UI, the alert will move to Pending. 
3. **Firing State**: After 1 minute (as defined in the `for` clause), the alert becomes Firing (Critical).

## Step C: Recovery

Restore the service to see the alert resolve automatically.

```bash
oc scale deployment hello --replicas=1 -n sample
```