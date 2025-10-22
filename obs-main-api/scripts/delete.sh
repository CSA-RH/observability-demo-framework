#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$(realpath "$(dirname "$0")")"
SOURCES_DIR=$SCRIPT_DIR/../app/
# Prerequisites
source $SCRIPT_DIR/env.sh

DEMO_NAMESPACE=$(oc project -q)
oc delete smon -n $DEMO_NAMESPACE --selector observability-demo-framework=agent
oc delete all -n $DEMO_NAMESPACE --selector observability-demo-framework=agent
oc delete secret -n $DEMO_NAMESPACE obs-demo-fw-state