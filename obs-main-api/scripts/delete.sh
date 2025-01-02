DEMO_NAMESPACE=observability-demo-2
oc delete smon -n $DEMO_NAMESPACE --selector observability-demo-framework=agent
oc delete all -n $DEMO_NAMESPACE --selector observability-demo-framework=agent
oc delete secret -n $DEMO_NAMESPACE obs-demo-fw-state