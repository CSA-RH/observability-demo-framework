# Custom platform alerts definition

In this folder we expose some examples of platform alerts samples. Those will be created as an alert group for the platform alerts via the AlertingRule CRD, to be allocated in thte `observability-monitor` namespace

- **CustomNodeCPUUsageCritical**. Triggers when node CPU usage exceeds 80% for more than 10 minutes
- **CustomNodeMemoryUsageCritical**. Triggers when node memory usage exceeds 80% for more than 10 minutes.
- **CustomVarDiskFullMoreThan90**. Alerts if the /var filesystem usage goes above 90%.
- **CustomPersistentVolumeFull**. Notifies when a PVC has less than 20% free space remaining.
- **CustomHighNodeIOWait**. Alerts when node CPU spends more than 20% of time waiting on I/O.
- **CustomKubeNodeUnreachable**. Fires when a node is marked unreachable by the API server for over 10 minutes.

```yaml
apiVersion: monitoring.openshift.io/v1
kind: AlertingRule
metadata:
  name: custom-platform-alerts
  namespace: openshift-monitoring
  labels: 
    platform-alerts: custom-set
spec:
  groups:
  - name: custom.rules
    rules:
    - alert: CustomNodeCPUUsageCritical
      expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
      for: 10m
      labels:
        severity: critical
      annotations:
        summary: "Node CPU usage is critical"
        description: "Node {{ $labels.instance }} CPU usage > 80% for more than 10m."

    - alert: CustomNodeMemoryUsageCritical
      expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 80
      for: 10m
      labels:
        severity: critical
      annotations:
        summary: "Node memory usage is critical"
        description: "Node {{ $labels.instance }} memory usage > 80% for more than 10m."

    - alert: CustomNodeVarDiskFullMoreThan90
      expr: (node_filesystem_size_bytes{mountpoint="/var",fstype!~"tmpfs|overlay"} - node_filesystem_avail_bytes{mountpoint="/var",fstype!~"tmpfs|overlay"}) 
            / node_filesystem_size_bytes{mountpoint="/var",fstype!~"tmpfs|overlay"} * 100 > 90
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "Node /var disk is almost full"
        description: "On {{ $labels.instance }}, /var usage > 90%."

    - alert: CustomPersistentVolumeFull
      expr: kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes * 100 > 80
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "Persistent Volume almost full"
        description: "PVC {{ $labels.persistentvolumeclaim }} in namespace {{ $labels.namespace }} has less than 20% free space remaining."

    - alert: CustomHighNodeIOWait
      expr: avg by(instance) (rate(node_cpu_seconds_total{mode="iowait"}[5m])) * 100 > 20
      for: 10m
      labels:
        severity: warning
      annotations:
        summary: "High I/O wait on node"
        description: "Node {{ $labels.instance }} CPU spent > 20% time in I/O wait over 10m."

    - alert: CustomKubeNodeUnreachable
      expr: kube_node_spec_taint{key="node.kubernetes.io/unreachable",effect="NoSchedule"} == 1
      for: 10m
      labels:
        severity: critical
      annotations:
        summary: "Kubernetes node unreachable"
        description: "Node {{ $labels.node }} has been unreachable for more than 10 minutes."
```

With this query, we can get all the rules defined as PrometheusRules in an Openshift cluster with their PrometheusRule CRD and namespace listed. 

```bash
oc get prometheusrule -A -oyaml | yq -r '
  .items[] |
  . as $promrule |
  (.. | select(has("alert") or has("record"))) as $rule |
  "\(.metadata.namespace): \(.metadata.name): \( ($rule.alert // $rule.record) )"
' 
```

# Testing

To check the alerts, we can patch the individual ones inside the group 

## 1. CustomNodeCPUUsageCritical

```bash
# Force firing (CPU < 80%)
oc -n openshift-monitoring patch alertingrule.monitoring.openshift.io custom-platform-alerts \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/groups/0/rules/0/expr", "value": "100 - (avg by(instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100) < 80"}]'
```

```bash
# Restore original (CPU > 80%)
oc -n openshift-monitoring patch alertingrule.monitoring.openshift.io custom-platform-alerts \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/groups/0/rules/0/expr", "value": "100 - (avg by(instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100) > 80"}]'
```

## 2. CustomNodeMemoryUsageCritical

```bash
# Force firing (memory usage < 80%)
oc -n openshift-monitoring patch alertingrule.monitoring.openshift.io custom-platform-alerts \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/groups/0/rules/1/expr", "value": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 < 80"}]'
```

```bash
# Restore original
oc -n openshift-monitoring patch alertingrule.monitoring.openshift.io custom-platform-alerts \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/groups/0/rules/1/expr", "value": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 80"}]'
```

## 3. CustomVarDiskFullMoreThan90

```bash
# Force firing (usage < 90%)
oc -n openshift-monitoring patch alertingrule.monitoring.openshift.io custom-platform-alerts \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/groups/0/rules/2/expr", "value": "(node_filesystem_avail_bytes{mountpoint=\"/var\",fstype!~\"tmpfs|overlay\"} / node_filesystem_size_bytes{mountpoint=\"/var\",fstype!~\"tmpfs|overlay\"}) * 100 > 10"}]'
```

```bash
# Restore original
oc -n openshift-monitoring patch alertingrule.monitoring.openshift.io custom-platform-alerts \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/groups/0/rules/2/expr", "value": "(node_filesystem_size_bytes{mountpoint=\"/var\",fstype!~\"tmpfs|overlay\"} - node_filesystem_avail_bytes{mountpoint=\"/var\",fstype!~\"tmpfs|overlay\"}) / node_filesystem_size_bytes{mountpoint=\"/var\",fstype!~\"tmpfs|overlay\"} * 100 > 90"}]'
```

## 4. CustomPersistentVolumeFull

Create a new namespace. 
```bash
# Create namespace
export NAMESPACE=test-pvc-$(echo $RANDOM)
oc new-project $NAMESPACE
cat <<EOF | oc create -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-pvc
  namespace: $NAMESPACE
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: managed-csi #ARO: CHANGE TO gp3-csi if ROSA or to equivalent if other. 
EOF
cat <<EOF | oc create -f -
apiVersion: v1
kind: Pod
metadata:
  name: pvc-tester
  namespace: $NAMESPACE
spec:
  containers:
  - name: pvc-tester
    image: registry.access.redhat.com/ubi8/ubi-minimal:latest
    command: [ "sleep", "infinity" ]
    volumeMounts:
    - name: test-volume
      mountPath: /test
  volumes:
  - name: test-volume
    persistentVolumeClaim:
      claimName: test-pvc
EOF
```

At this time, there will be no alert firing, but we can fill the disk with dummy data

```bash
# Fill 900MB
oc exec pvc-tester -- dd if=/dev/urandom of=/test/dummyfile bs=1M count=900
```

For checking how much storage is consumed in the pod filesystem

```bash
# Check usage
oc exec pvc-tester -- df -h /test
```

## 5. CustomHighNodeIOWait

```bash
# Force firing (iowait < 20%)
oc -n openshift-monitoring patch alertingrule.monitoring.openshift.io custom-platform-alerts \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/groups/0/rules/4/expr", "value": "avg by(instance) (rate(node_cpu_seconds_total{mode=\"iowait\"}[5m])) * 100 < 20"}]'
```

```bash
# Restore original
oc -n openshift-monitoring patch alertingrule.monitoring.openshift.io custom-platform-alerts \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/groups/0/rules/4/expr", "value": "avg by(instance) (rate(node_cpu_seconds_total{mode=\"iowait\"}[5m])) * 100 > 20"}]'
```


## 6. CustomKubeNodeUnreachable

We modify the rule to check for a fake taint, very similar to the one applied by the API and then set the alert to check if that taint exists. 

Modify the rule to check for the taint fake-unreachable. 
```bash
oc -n openshift-monitoring patch alertingrule.monitoring.openshift.io custom-platform-alerts \
  --type='json' \
  -p='[{"op":"replace","path":"/spec/groups/0/rules/5/expr","value":"kube_node_spec_taint{key=\"fake-unreachable\",effect=\"NoSchedule\"} == 1"}]'
```

Pick a random node and taint with fake-unreachable
```bash
#Pick a random node
UNSCHEDULABLE_NODE=$(oc get nodes -l node-role.kubernetes.io/worker= -o jsonpath='{.items[*].metadata.name}' \
  | tr ' ' '\n' \
  | awk -v seed=$RANDOM 'BEGIN{srand(seed)} {a[NR]=$0} END{print a[int(rand()*NR)+1]}')
echo NODE TO BE TAINTED: $UNSCHEDULABLE_NODE
oc adm taint nodes $UNSCHEDULABLE_NODE fake-unreachable=true:NoSchedule
```

Here, wait for the alert to be fired. 

Remove the taint

```bash
oc adm taint nodes $UNSCHEDULABLE_NODE fake-unreachable-

```

Restore the original alert

```bash
oc -n openshift-monitoring patch alertingrule.monitoring.openshift.io custom-platform-alerts \
  --type='json' \
  -p='[{"op":"replace","path":"/spec/groups/0/rules/5/expr","value":"kube_node_spec_taint{key=\"node.kubernetes.io/unreachable\",effect=\"NoSchedule\"} == 1"}]'
```


