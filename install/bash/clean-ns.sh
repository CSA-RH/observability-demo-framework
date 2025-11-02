NAMESPACES_TO_DELETE=("openshift-logging" "openshift-loki-operator" "openshift-tempo-operator" "openshift-opentelemetry-operator")

for ns in ${NAMESPACES_TO_DELETE[@]}; do
    echo Deleting namespace $ns...
    oc delete ns $ns
done