METRICS_API_ENDPOINT=http://localhost:8080  # Or any other
curl -i -X GET $METRICS_API_ENDPOINT/metrics && echo && echo
curl -i -X GET $METRICS_API_ENDPOINT/metrics/not-existent-metric && echo && echo
curl -i -X POST $METRICS_API_ENDPOINT/metrics/new-metric?value=10 && echo && echo
curl -i -X POST $METRICS_API_ENDPOINT/metrics/new-metric?value=10 && echo && echo
curl -i -X GET $METRICS_API_ENDPOINT/metrics/new-metric && echo && echo
curl -i -X PATCH $METRICS_API_ENDPOINT/metrics/new-metric?value=12 && echo && echo
curl -i -X PATCH $METRICS_API_ENDPOINT/metrics/not-existent-metric&value=13 && echo && echo
curl -i -X DELETE $METRICS_API_ENDPOINT/metrics/new-metric && echo && echo
curl -i -X DELETE $METRICS_API_ENDPOINT/metrics/new-metric && echo && echo
curl -i -X DELETE $METRICS_API_ENDPOINT/metrics/not-existent-metric && echo && echo
curl -i -X POST $METRICS_API_ENDPOINT/metrics/metric-1?value=20 && echo && echo
curl -i -X POST $METRICS_API_ENDPOINT/metrics/metric-2?value=30 && echo && echo
curl -i -X POST $METRICS_API_ENDPOINT/metrics/metric-3?value=40 && echo && echo
curl -i -X POST $METRICS_API_ENDPOINT/metrics/metric-4?value=50 && echo && echo
curl -i -X GET $METRICS_API_ENDPOINT/metrics && echo && echo