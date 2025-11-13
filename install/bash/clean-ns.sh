#!/bin/bash
source ./env.sh

oc delete tempostack -n obs-demo escotilla
oc delete opentelemetrycollector otel -n obs-demo

NAMESPACES_TO_DELETE=("openshift-logging" "openshift-loki-operator" "openshift-tempo-operator" "openshift-opentelemetry-operator" "obs-demo")

for ns in ${NAMESPACES_TO_DELETE[@]}; do
    echo Deleting namespace $ns...
    oc delete ns $ns
done