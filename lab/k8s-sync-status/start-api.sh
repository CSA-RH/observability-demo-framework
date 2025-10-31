#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$(realpath "$(dirname "$0")")"
# Activate environment (python and oc)
source $SCRIPT_DIR/env.sh

pip3 install -r "$SCRIPT_DIR/requirements.txt"

uvicorn main:app --reload