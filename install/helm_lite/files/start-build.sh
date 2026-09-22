#!/bin/sh
set -eu

echo "Starting build for $BC_NAME..."

# 1. Initialize an empty string for our build args
BUILD_ARGS_STRING=""

# 2. Get the list of all variable NAMES that start with "OBS_BUILD_"
#    (e.g., "OBS_BUILD_VITE_KEYCLOAK_URL OBS_BUILD_VITE_OBSERVABILITY_DEMO_API")
VAR_NAME_LIST=$(printenv | grep '^OBS_BUILD_' | cut -d'=' -f1)

# 3. Loop over this list of names IN THE MAIN SHELL
for VAR_NAME in $VAR_NAME_LIST; do
    
    # 4. Use 'eval' to get the value of the variable named by $VAR_NAME
    #    This is the correct way to do indirection in 'sh'
    eval "VAR_VALUE=\$$VAR_NAME"
    echo "Found var: $VAR_NAME"

    # 5. Remove the "OBS_BUILD_" prefix
    ARG_NAME=$(echo "$VAR_NAME" | sed 's/^OBS_BUILD_//')
    echo "Arg Name: $ARG_NAME"

    # 6. Append the formatted argument to our string
    BUILD_ARGS_STRING="$BUILD_ARGS_STRING --build-arg=${ARG_NAME}=\"${VAR_VALUE}\""
done

# 7. Now, the rest of the script can see the populated variable
if [ -n "$BUILD_ARGS_STRING" ]; then
    echo "Starting build with dynamic args: $BUILD_ARGS_STRING"
fi

# 8. Construct the full command as a string
OC_COMMAND="oc start-build $BC_NAME -n ${PROJECT_NAME} $BUILD_ARGS_STRING --follow=false"
echo $OC_COMMAND

# 9. Use 'eval' to execute the command. This allows the shell
#    to correctly parse the quoted arguments in $BUILD_ARGS_STRING.
BUILD_NAME=$(eval "$OC_COMMAND" | awk -F'/' '{print $2}' | awk '{print $1}')

if [ -z "$BUILD_NAME" ]; then
    echo "Failed to start build."
    exit 1
fi

echo "Build $BUILD_NAME started. Waiting for it to complete..."

# Wait for the build to complete or fail
oc wait --for=condition=Complete --timeout=5m build/$BUILD_NAME -n $PROJECT_NAME

echo "✅ Build $BUILD_NAME completed successfully."
