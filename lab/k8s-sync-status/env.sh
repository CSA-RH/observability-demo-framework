#!/bin/bash

# -- Prerequisites check
oc whoami > /dev/null 2>&1
# Check the exit status of the previous command ($?)
if [ $? -ne 0 ]; then
    echo "ERROR: oc tool is not logged in or cannot connect to the cluster." >&2
    echo "Please run 'oc login' or ensure your current configuration is valid." >&2
    exit 1
fi

echo "Successfully verified oc login. Continuing script execution..."

# --- Configuration ---
VENV_DIR=".venv"
PYTHON_CMD="python3" # Change to "python" if needed
# ---------------------

ACTIVATE_FILE="$VENV_DIR/bin/activate"

if [ ! -f "$ACTIVATE_FILE" ]; then
    echo "Virtual environment not found at '$VENV_DIR'."
    echo "Creating virtual environment..."
    
    # 2. Create the virtual environment
    $PYTHON_CMD -m venv "$VENV_DIR"
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment." >&2
        return 1 # Use 'return' to stop the script without exiting the shell
    fi
    echo "Virtual environment created successfully."
else
    echo "Virtual environment found."
fi

# 3. Activate the virtual environment
echo "Activating virtual environment..."
source "$ACTIVATE_FILE"