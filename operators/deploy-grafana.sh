source ./vars.sh
echo ...GRAFANA OPERATOR AND GrafanaDatasources for Loki and Tempo...
if check_openshift_resource_exists Subscription grafana-operator openshift-operators; then
  echo " - Grafana Community Operator already installed"
else
  cat <<EOF | oc create -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  labels:
    operators.coreos.com/grafana-operator.openshift-operators: ""
    observability-demo-framework: 'operator'
  name: grafana-operator
  namespace: openshift-operators
spec:
  channel: v5
  installPlanApproval: Automatic
  name: grafana-operator
  source: community-operators
  sourceNamespace: openshift-marketplace
  startingCSV: grafana-operator.v5.16.0
EOF
  # Wait for the operator to be created and available. 
  wait_operator_to_be_installed operators.coreos.com/grafana-operator.openshift-operators openshift-operators
fi

# Create a Grafana instance
echo " - Create a Grafana instance"
cat <<EOF | oc apply -f -
apiVersion: grafana.integreatly.org/v1beta1
kind: Grafana
metadata:
  labels:
    dashboards: grafana-escotilla
    folders: grafana-escotilla
    observability-demo-framework: 'grafana'
  name: grafana-escotilla
  namespace: $CURRENT_NAMESPACE
spec:
  config:
    auth:
      disable_login_form: 'false'
    log:
      mode: console
    security:
      admin_password: start
      admin_user: root
  version: 'docker.io/grafana/grafana@sha256:a0f881232a6fb71a0554a47d0fe2203b6888fe77f4cefb7ea62bed7eb54e13c3'
EOF

echo " - Create/Configure secure route to Grafana"
cat <<EOF | oc apply -f -
kind: Route
apiVersion: route.openshift.io/v1
metadata:
  name: grafana
  namespace: $CURRENT_NAMESPACE  
  labels:
    app.kubernetes.io/managed-by: grafana-operator
    observability-demo-framework: 'grafana'  
spec:
  to:
    kind: Service
    name: grafana-escotilla-service
    weight: 100
  port:
    targetPort: grafana
  tls:
    termination: edge
EOF

#   We put as the Grafana Datasource endpoint, 
#   the query-frontend service DNS address within  
#   the cluster for Grafana and we use the Client certificates in the secrets. 
# For Tempo: secret $APP_NAMESPACE/tempo-escotilla-gateway-mtls

# Exporting Grafana Datasource for Tempo
export TEMPO_TLS_SECRET=tempo-escotilla-gateway-mtls
export TEMPO_TLS_CERT=./output/tempo-tls.crt
export TEMPO_TLS_KEY=./output/tempo-tls.key
# - Get Cert and Key from the secret
oc get secret/$TEMPO_TLS_SECRET \
    -n $CURRENT_NAMESPACE \
    -ojsonpath='{.data.tls\.crt}' \
    | base64 -d > $TEMPO_TLS_CERT
oc get secret/$TEMPO_TLS_SECRET \
    -n $CURRENT_NAMESPACE \
    -ojsonpath='{.data.tls\.key}' \
    | base64 -d > $TEMPO_TLS_KEY

yq '.spec.datasource.secureJsonData.tlsClientCert |= loadstr(strenv(TEMPO_TLS_CERT))' ./templates/ds-tempo.yaml \
| yq '.spec.datasource.secureJsonData.tlsClientKey |= loadstr(strenv(TEMPO_TLS_KEY))' > ./output/ds-grafana-tempo.yaml

# Exporting Grafana Datasource for Loki
export LOKI_TLS_SECRET=loki-gateway-client-http
export LOKI_TLS_CERT=./output/loki-tls.crt
export LOKI_TLS_KEY=./output/loki-tls.key
oc get secret/$LOKI_TLS_SECRET \
    -n openshift-logging \
    -ojsonpath='{.data.tls\.crt}' \
    | base64 -d > $LOKI_TLS_CERT
oc get secret/$LOKI_TLS_SECRET \
    -n openshift-logging \
    -ojsonpath='{.data.tls\.key}' \
    | base64 -d > $LOKI_TLS_KEY

yq '.spec.datasource.secureJsonData.tlsClientCert |= loadstr(strenv(LOKI_TLS_CERT))' ./templates/ds-loki.yaml \
| yq '.spec.datasource.secureJsonData.tlsClientKey |= loadstr(strenv(LOKI_TLS_KEY))' > ./output/ds-grafana-loki.yaml

# Apply changes in the cluster
oc apply -f ./output/

# Retrieve UIDs and patch the deployments
while [ -z "$LOKI_DS_UID" ]; do
  export LOKI_DS_UID=$(oc get grafanadatasource -n $CURRENT_NAMESPACE ds-grafana-loki -ojsonpath='{.status.uid}')
  sleep 2
done
echo "Loki UID: $LOKI_DS_UID"

while [ -z "$TEMPO_DS_UID" ]; do
  export TEMPO_DS_UID=$(oc get grafanadatasource -n $CURRENT_NAMESPACE ds-grafana-tempo -ojsonpath='{.status.uid}')
  sleep 2
done
echo "Tempo UID: $TEMPO_DS_UID"

# Patch both deployments. 

oc patch GrafanaDatasource ds-grafana-tempo \
  -n $CURRENT_NAMESPACE \
  --type='merge' \
  -p "$(echo '{"spec":{"datasource":{"url": "https://tempo-escotilla-query-frontend.'$CURRENT_NAMESPACE'.svc.cluster.local:3200", "jsonData":{"serverName": "tempo-escotilla-gateway.'$CURRENT_NAMESPACE'.svc.cluster.local", "tracesToLogsV2":{"datasourceUid":"'"$LOKI_DS_UID"'"}}}}}' )"

oc patch GrafanaDatasource ds-grafana-loki \
  -n $CURRENT_NAMESPACE \
  --type='merge' \
  -p "$(echo '{"spec":{"datasource":{"jsonData":{"derivedFields":[{"name":"TraceID","matcherType":"regex","matcherRegex":"\"traceid\":\"([a-f0-9]{32})\"","url":"/explore?schemaVersion=1&panes={\"nm1\":{\"datasource\":\"'"$TEMPO_DS_UID"'\",\"queries\":[{\"refId\":\"A\",\"datasource\":{\"type\":\"tempo\",\"uid\":\"'"$TEMPO_DS_UID"'\"},\"queryType\":\"traceql\",\"limit\":20,\"tableType\":\"traces\",\"query\":\"${__value.raw}\"}],\"range\":{\"from\":\"now-1h\",\"to\":\"now\"}}}&orgId=1","urlDisplayLabel":"Tempo"}]}}}}')"