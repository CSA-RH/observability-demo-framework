#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$(realpath "$(dirname "$0")")"
SOURCES_DIR=$SCRIPT_DIR/../app/

# Prerequisites
source $SCRIPT_DIR/env.sh
source $SOURCES_DIR/.venv/bin/activate
pip3 install -r "$SCRIPT_DIR/../app/requirements.txt"

# Run the FastAPI app using Uvicorn, specifying the app directory
uvicorn main:app --reload --app-dir "$SCRIPT_DIR/../app"