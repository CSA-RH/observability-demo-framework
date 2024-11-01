"use strict";

// imports
const express = require('express')
const axios = require('axios');
const { MeterRegistry } = require('@opentelemetry/metrics');
const { PrometheusExporter } = require('@opentelemetry/exporter-prometheus');
const { v4: uuidv4 } = require('uuid');

const metricOrigin = "src"
console.log("Environment: " + metricOrigin);

// set up prometheus 
const prometheusPort = 8081;
const app = express();

var _dict = {}
var _meter = {}
var _labels = {}
const _agents = new Map()

function initializePrometheusEndpoint() {

    _meter = new MeterRegistry().getMeter('example-prometheus');
    const exporter = new PrometheusExporter(
        {
            startServer: true,
            port: prometheusPort
        },
        () => {
            console.log("prometheus scrape endpoint: http://0.0.0.0:"
                + prometheusPort
                + "/metrics");
        }
    );
    _meter.addExporter(exporter);
    _labels = _meter.labels({ metricOrigin: metricOrigin });
    _dict = {}
}

function getAllMetrics(req, res) {
    var results = [];
    for (var metricName in _dict) {
        const result = {
            name: metricName,
            value: _dict[metricName].bind(_labels)._data.toString()
        };
        results.push(result);
    }
    res.status(200).send(JSON.stringify(results))
}

function getMetric(req, res) {
    const metricName = req.params.metricName;
    if (metricName in _dict) {
        res.status(200).send(_dict[metricName].bind(_labels)._data.toString());
    }
    else {
        res.status(404).send("Not found")
    }
}

function postMetric(req, res) {
    const metricName = req.params.metricName;
    const valueRaw = req.query.value;
    const value = parseInt(valueRaw);
    if (metricName in _dict) {
        res.status(409).send("Cannot create metric " + metricName + ". Already created");
    }
    else {
        _dict[metricName] = {}
        const newMetric = _meter.createGauge(metricName, {
            monotonic: false,
            labelKeys: ["metricOrigin"],
            description: "Metric " + metricName
        });
        newMetric.bind(_labels).set(value)
        _dict[metricName] = newMetric;
        res.status(200).send("Created metric " + metricName + " with value " + value);
    }
}

function putMetric(req, res) {
    const metricName = req.params.metricName;
    const valueRaw = req.query.value;
    const value = parseInt(valueRaw);
    if (metricName in _dict) {
        _dict[metricName].bind(_labels).set(value);
        res.status(200).send("Modified metric " + metricName + " with value " + value);
    }
    else {
        res.status(404).send("Cannot modify metric " + metricName + ". Not found");
    }
}

function deleteMetric(req, res) {
    initializePrometheusEndpoint()
    res.status(200).send("Delete operation too destructive");
}

function getRegisteredAgents(req, res) {
    res.status(200).send(JSON.stringify(Object.fromEntries(_agents)));
}

function postAgent(req, res) {
    const agentId = req.params.agentId;
    const agentInfo = req.body
    const ip = agentInfo.ip;
    const port = agentInfo.port;
    if (ip == null || port == null) {
        res.status(400).send("Valid IP and Port required.");
        return;
    }
    _agents.set(agentId, { ip: ip, port: port });

    res.status(200).send();
}

function deleteAgent(req, res) {
    const agentId = req.params.agentId;
    _agents.delete(agentId);
    res.status(200).send();
}

function kick(req, res) {
    var kickCount = req.body.count
    if (kickCount == null)
        kickCount = 3; // Default kickCount
    else if (kickCount == 0) {
        console.log ("no more kicks");
        res.status(200).send();
        return;
    }        
    var agentReceived = req.body.sender;
    if (agentReceived == null) 
        agentReceived = "INITIAL KICK";
    const sender = process.env.HOSTNAME
    console.log("---");    
    console.log("Sent by " + agentReceived + ". Kicks remaining: " + kickCount);    
    for (const [agentId, agentInfo] of _agents.entries()) {                
        var post_data = {
            sender : sender,
            count : kickCount-1            
        };        
        const agentRequestId = uuidv4();        
        console.log("[", agentRequestId, "][REQUEST from ", sender, " to ", agentId)      
        axios.post("http://" + agentInfo.ip + ":" + agentInfo.port + "/kick", post_data)
            .then(agentResponse => {                
                console.log("[", agentRequestId, "][RESPONSE from ", agentId,"]: Status =", agentResponse.status)                
            })
            .catch(error => {
                console.error("Error: " + error);
            });
    }
    res.status(200).send();
}

initializePrometheusEndpoint();
app.use(express.json());

// ROUTES
app.get('/', (req, res) => {
    res.status(200).send("API Metrics management")
});
app.get("/metrics", getAllMetrics);
app.get("/metrics/:metricName", getMetric);
app.post("/metrics/:metricName", postMetric);
app.put("/metrics/:metricName", putMetric);
app.delete("/metrics/:metricName", deleteMetric);

// Register agents. 
app.get("/agents", getRegisteredAgents);
app.post("/agents/:agentId", postAgent);
app.delete("/agents/:agentId", deleteAgent);
// kick operation
app.post("/kick", kick);

app.listen(8080, () => console.log(`API for Observability Framework Demo at 8080!\nPrometheus endpoint at 8081`))