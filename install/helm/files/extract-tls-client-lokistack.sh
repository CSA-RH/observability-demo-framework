#!/bin/sh
set -eu

# Export the LokiStack logging service CA into the target namespace
export SERVICE_CA_FILE=/tmp/service-ca.crt
oc get configmap logging-ca-bundle \
   -n openshift-logging \
   -ojsonpath='{.data.service-ca\.crt}'  \
   > $SERVICE_CA_FILE

oc create configmap logging-ca-bundle \
   -n $NAMESPACE \
   --from-file=$SERVICE_CA_FILE \
   -oyaml \
   --dry-run=client \
   | oc apply -f -
echo CONFIGMAP updated

# Export the LokiStack Gateway Client TLS certificate into the target namespace
export CLIENT_TLS_CRT_FILE=/tmp/logging-client-tls.crt
export CLIENT_TLS_KEY_FILE=/tmp/logging-client-tls.key
oc get secret logging-gateway-client-http \
   -n openshift-logging \
   -ojsonpath='{.data.tls\.crt}' | base64 -d \
   > $CLIENT_TLS_CRT_FILE
echo CLIENT CERTIFICATE DEFINITION retrieved
oc get secret logging-gateway-client-http \
   -n openshift-logging \
   -ojsonpath='{.data.tls\.key}' | base64 -d \
   > $CLIENT_TLS_KEY_FILE
echo CLIENT CERTIFICATE KEY retrieved
oc create secret tls logging-gateway-client-http \
   -n $NAMESPACE \
   --cert=$CLIENT_TLS_CRT_FILE \
   --key=$CLIENT_TLS_KEY_FILE \
   -oyaml \
   --dry-run=client \
   | oc apply -f -
echo CLIENT CERTIFICATE DEFINITION updated