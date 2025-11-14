For testing purposes, check `minio-dev.yaml` simply by executing `oc apply -f minio-dev.yaml`

For the helm chart, add the values 
```bash
helm install obs-minio minio/minio \
  --namespace minio \
  --create-namespace \
  -f obs-values.yaml
```

Examples for Loki and Tempo

```bash
# Loki
oc create secret generic -n openshift-logging lokistack-minio \
  --from-literal=bucketnames="loki-storage" \
  --from-literal=endpoint="http://obs-minio.minio.svc:9000" \
  --from-literal=access_key_id="minioadmin" \
  --from-literal=access_key_secret="minioadmin123"

# Tempo
oc create secret generic -n obs-demo tempostack-minio \
  --from-literal=bucket="tempo-storage" \
  --from-literal=endpoint="http://obs-minio.minio.svc:9000" \
  --from-literal=access_key_id="minioadmin" \
  --from-literal=access_key_secret="minioadmin123"
```

YAML Secret for LokiStack

```yaml
kind: Secret
apiVersion: v1
metadata:
  name: lokistack-minio
  namespace: openshift-logging
  uid: c07768cd-ab5a-422c-a064-1376aeafc603
  resourceVersion: '21482020'
  creationTimestamp: '2025-11-03T17:22:11Z'
  managedFields:
    - manager: kubectl-create
      operation: Update
      apiVersion: v1
      time: '2025-11-03T17:22:11Z'
      fieldsType: FieldsV1
      fieldsV1:
        'f:data':
          .: {}
          'f:access_key_id': {}
          'f:access_key_secret': {}
          'f:bucketnames': {}
          'f:endpoint': {}
        'f:type': {}
data:
  access_key_id: bWluaW9hZG1pbg==
  access_key_secret: bWluaW9hZG1pbjEyMw==
  bucketnames: bG9raS1zdG9yYWdl
  endpoint: aHR0cDovL29icy1taW5pby5taW5pby5zdmM6OTAwMA==
type: Opaque
```

About the LokiStack
```yaml
    secret:
      name: lokistack-minio
      type: s3
```

About the subscription. 

```yaml
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:    
  labels:
    operators.coreos.com/loki-operator.openshift-loki-operator: ""
    observability-demo-framework: 'operator'
  name: loki-operator
  namespace: openshift-loki-operator
spec:
  channel: stable-6.1
  installPlanApproval: Automatic
  name: loki-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
  startingCSV: loki-operator.v6.1.1
```


```bash
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
      name: lokistack-minio
      type: s3
  hashRing:
    type: memberlist
  size: 1x.demo
  storageClassName: managed-csi
EOF
```