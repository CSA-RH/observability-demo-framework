#!/bin/sh
set -eu

echo "Starting build for $BC_NAME..."

# --- This is the new dynamic logic ---
# 1. Initialize an empty string for our build args
BUILD_ARGS_STRING=""

# 2. Find all env vars starting with "BUILD_",
#    then loop through them.
printenv | grep '^BUILD_' | while read -r line; do
    # 3. Get the var name (e.g., "BUILD_VITE_KEYCLOAK_URL")
    VAR_NAME=$(echo "$line" | cut -d'=' -f1)
    
    # 4. Get the var value (e.g., "https://keycloak.example.com")
    VAR_VALUE=$(echo "$line" | cut -d'=' -f2-)
    
    # 5. Remove the "BUILD_" prefix (e.g., "VITE_KEYCLOAK_URL")
    ARG_NAME=$(echo "$VAR_NAME" | sed 's/^BUILD_//')
    
    # 6. Append the formatted argument to our string
    #    We quote the value to handle spaces or special characters
    BUILD_ARGS_STRING="$BUILD_ARGS_STRING --build-arg=${ARG_NAME}=\"${VAR_VALUE}\""
done
# --- End of dynamic logic ---

if [ -n "$BUILD_ARGS_STRING" ]; then
    echo "Starting build with dynamic args: $BUILD_ARGS_STRING"
fi

# 7. Construct the full command as a string
OC_COMMAND="oc start-build $BC_NAME -n {{ .Release.Namespace }} $BUILD_ARGS_STRING --follow=false"

# 8. Use 'eval' to execute the command. This allows the shell
#    to correctly parse the quoted arguments in $BUILD_ARGS_STRING.
#    The output of this eval is piped to awk.
BUILD_NAME=$(eval "$OC_COMMAND" | awk -F'/' '{print $2}' | awk '{print $1}')

if [ -z "$BUILD_NAME" ]; then
    echo "Failed to start build."
    exit 1
fi

echo "Build $BUILD_NAME started. Waiting for it to complete..."

# Wait for the build to complete or fail
oc wait --for=condition=Complete --timeout=5m build/$BUILD_NAME -n {{ .Release.Namespace }}

echo "✅ Build $BUILD_NAME completed successfully."