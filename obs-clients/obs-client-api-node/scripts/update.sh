# Resources cleanup
rm -rf build node_modules package-lock.json .env
# Delete previous ImageStreamTags
oc delete ImageStreamTag obs-client-node:latest
# Remove previous build objects
oc delete build --selector build=obs-client-node > /dev/null 
# Start build for obs-client-node
oc start-build obs-client-node --from-file .
# Follow the logs until completion 
oc logs $(oc get build --selector build=obs-client-node -oNAME) -f