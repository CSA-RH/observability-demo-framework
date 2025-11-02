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