# Create ImageStream for kc-client
cat <<EOF | oc apply -f -
apiVersion: image.openshift.io/v1
kind: ImageStream
metadata:
  name: obs-client-node
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
    build: obs-client-node
  name: obs-client-node
spec:
  output:
    to:
      kind: ImageStreamTag
      name: obs-client-node:latest
  source:
    binary: {}
    type: Binary
  strategy:
    dockerStrategy: 
      dockerfilePath: Dockerfile
    type: Docker
EOF
# Resources cleanup
rm -rf build node_modules package-lock.json .env
# Remove previous build objects
oc delete build --selector build=obs-client-node > /dev/null 
# Start build for obs-client-node
oc start-build obs-client-node --from-file .
# Follow the logs until completion 
oc logs $(oc get build --selector build=obs-client-node -oNAME) -f 