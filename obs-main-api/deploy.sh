# Create ImageStream for kc-client
cat <<EOF | oc apply -f -
apiVersion: image.openshift.io/v1
kind: ImageStream
metadata:
  name: obs-main-api
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
    build: obs-main-api
  name: obs-main-api
spec:
  output:
    to:
      kind: ImageStreamTag
      name: obs-main-api:latest
  source:
    binary: {}
    type: Binary
  strategy:
    dockerStrategy: 
      dockerfilePath: Dockerfile
    type: Docker
EOF
# Remove previous build objects
oc delete build --selector build=obs-main-api > /dev/null 
# Start build for obs-main-api
oc start-build obs-main-api --from-file .
# Follow the logs until completion 
oc logs $(oc get build --selector build=obs-main-api -oNAME) -f 
# Create deployment
oc create deploy obs-main-api --image=obs-main-api:latest 
# Create service
oc expose deploy/obs-main-api --port 8000
# Create route
cat <<EOF | oc apply -f - 
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  labels:
    app: obs-main-api
  name: obs-main-api
spec:
  port:
    targetPort: 8000
  to:
    kind: Service
    name: obs-main-api
  tls: 
    termination: edge
EOF