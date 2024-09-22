curl --header "Content-Type: application/json" -i -X POST localhost:8080/agents/fernando-sanz -d '{"ip": "127.0.0.1", "port": 8080}'
curl --header "Content-Type: application/json" -i -X POST localhost:8080/agents/ben-barek -d '{"ip": "127.0.0.1", "port": 8080}'
curl --header "Content-Type: application/json" -i -X POST localhost:8080/agents/viberti -d '{"ip": "127.0.0.1", "port": 8080}'
curl --header "Content-Type: application/json" -i -X POST localhost:8080/kick

