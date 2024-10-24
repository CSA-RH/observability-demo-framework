# Create ImageStream for Observability dotnet
cat <<EOF | oc apply -f -
apiVersion: image.openshift.io/v1
kind: ImageStream
metadata:
  name: obs-client-dotnet
spec:
  lookupPolicy:
    local: true
EOF
# Create BuildConfig for kc-client
cat <<EOF | oc apply -f - 
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  labels:
    build: obs-client-dotnet
  name: obs-client-dotnet
spec:
  output:
    to:
      kind: ImageStreamTag
      name: obs-client-dotnet:latest
  source:
    binary: {}
    type: Binary
  strategy:
    dockerStrategy: 
      dockerfilePath: Dockerfile
    type: Docker
EOF
# Resources cleanup
rm -rf bin out obj
# Remove previous build objects
oc delete build --selector build=obs-client-dotnet > /dev/null 
# Start build for obs-client-dotnet
oc start-build obs-client-dotnet --from-file .
# Follow the logs until completion 
oc logs $(oc get build --selector build=obs-client-dotnet -oNAME) -f 