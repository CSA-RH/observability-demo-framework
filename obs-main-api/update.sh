# Remove previous build objects
oc delete build --selector build=obs-main-api > /dev/null 
# Start build for obs-main-api
oc start-build obs-main-api --from-file .
# Follow the logs until completion 
oc logs $(oc get build --selector build=obs-main-api -oNAME) -f 
# update deployment
oc set image \
  deployment/obs-main-api \
  obs-main-api=$(oc get istag obs-main-api:latest -o jsonpath='{.image.dockerImageReference}')