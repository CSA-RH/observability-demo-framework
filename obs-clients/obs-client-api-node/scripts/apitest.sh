METRICS_API_ENDPOINT=http://localhost:8080  # Or any other
curl -i -X GET $METRICS_API_ENDPOINT/metrics && echo && echo
curl -i -X GET $METRICS_API_ENDPOINT/metrics/notexistentmetric && echo && echo
curl -i -X POST $METRICS_API_ENDPOINT/metrics/newmetric?value=10 && echo && echo
curl -i -X POST $METRICS_API_ENDPOINT/metrics/newmetric?value=10 && echo && echo
curl -i -X GET $METRICS_API_ENDPOINT/metrics/newmetric && echo && echo
curl -i -X PUT $METRICS_API_ENDPOINT/metrics/newmetric?value=12 && echo && echo
curl -i -X PUT $METRICS_API_ENDPOINT/metrics/notexistentmetric&value=13 && echo && echo
curl -i -X DELETE $METRICS_API_ENDPOINT/metrics/newmetric && echo && echo
curl -i -X DELETE $METRICS_API_ENDPOINT/metrics/newmetric && echo && echo
curl -i -X DELETE $METRICS_API_ENDPOINT/metrics/notexistentmetric && echo && echo
curl -i -X POST $METRICS_API_ENDPOINT/metrics/metric1?value=20 && echo && echo
curl -i -X POST $METRICS_API_ENDPOINT/metrics/metric2?value=30 && echo && echo
curl -i -X POST $METRICS_API_ENDPOINT/metrics/metric3?value=40 && echo && echo
curl -i -X POST $METRICS_API_ENDPOINT/metrics/metric4?value=50 && echo && echo
curl -i -X GET $METRICS_API_ENDPOINT/metrics && echo && echo

curl --header "Content-Type: application/json" \
  -X POST \
  --data '{"ip":"10.0.100.1","port":8080}' \
  $METRICS_API_ENDPOINT/agents/agent1
echo && echo

curl --header "Content-Type: application/json" \
  -X POST \
  --data '{"ip":"10.0.100.2","port":8080}' \
  $METRICS_API_ENDPOINT/agents/agent2
echo && echo

curl --header "Content-Type: application/json" \
  -X POST \
  --data '{"ip":"10.0.100.3","port":8080}' \
  $METRICS_API_ENDPOINT/agents/agent3
echo && echo

curl -i -X GET $METRICS_API_ENDPOINT/agents 
echo && echo

curl -i -X DELETE $METRICS_API_ENDPOINT/agents/agent2 
echo && echo

curl -i -X GET $METRICS_API_ENDPOINT/agents 
echo && echo

curl --header "Content-Type: application/json" \
    -i -X POST $METRICS_API_ENDPOINT/kick \
    --data '{"counter": 0, "sender": "viberti"}' 
echo && echo