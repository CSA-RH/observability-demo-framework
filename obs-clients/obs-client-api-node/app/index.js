"use strict";

// imports
const express = require('express')
const axios = require('axios');
const { MeterRegistry } = require('@opentelemetry/metrics');
const { PrometheusExporter } = require('@opentelemetry/exporter-prometheus');
const { v4: uuidv4 } = require('uuid');

const { LoggerProvider, SimpleLogRecordProcessor } = require('@opentelemetry/sdk-logs');
const { OTLPLogExporter } = require('@opentelemetry/exporter-logs-otlp-http');

// Create a logger provider
const loggerProvider = new LoggerProvider();

// Configure the OTLP log exporter
const logExporter = new OTLPLogExporter({
  url: process.env.OTEL_EXPORTER_OTLP_LOGS_ENDPOINT, // OTel Collector endpoint
});

// Add a processor to export logs
loggerProvider.addLogRecordProcessor(new SimpleLogRecordProcessor(logExporter));

// Get a logger
const logger = loggerProvider.getLogger('node-logger');

const originConsoleError = console.error;
const originConsoleLog = console.log;

// Custom logging function
function customLog(severityText, message) {
    // Log to OpenTelemetry
    logger.emit({
      body: message,
      severityNumber: severityText === 'ERROR' ? 16 : 1, // ERROR=16, INFO=1
      severityText
    });

    // Log to console
    if (severityText === 'ERROR') {
        originConsoleError(`[${severityText}] ${message}`);
    } else {
        originConsoleLog(`[${severityText}] ${message}`);
    }
  }

// Override console.log and console.error
console.log = (message) => customLog('INFO', message);
console.error = (message) => customLog('ERROR', message);

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

function order(req, res) {
    const customer = process.env.HOSTNAME
    const requestId = crypto.randomUUID(); 
    const waiter = getAvailableWaiter(_agents);
    
    console.log(`[${requestId}] Ordering a tasting menu...`)    
    if (!waiter) {
        console.error(`[${requestId}] There is no waiter available. I'm getting hungry and angry!`)
        res.status(404).send("No waiter available");
        return;
    }
    console.log(`[${requestId}] Request the waiter ${waiter.name} a tasting menu`)
    // Requesting service
    const postData = {
        customer : customer,
        requestId: requestId,
        waiter: waiter.name
    };
    console.log("----")
    console.log(JSON.stringify(postData, null, 4));
    console.log("----")
    axios.post("http://" + waiter.ip + ":" + waiter.port + "/operations/request", postData)
        .then(agentResponse => {                
            console.log(`[${requestId}] It was soooo good, almost as good as at Camperos Juanma!`);            
            res.status(200).send(); return;
        })
        .catch(error => {
            console.error(`[${requestId}] Something went wrong: ${error}`);            
            res.status(400).send();
            return;
        });
}

function request(req, res){
    const waiter = process.env.HOSTNAME;
    const cook = getAvailableCook(_agents);
    const customerRequest = req.body;
    const requestId = customerRequest?.requestId;

    if (!requestId) {
        console.error(`[N/A] Error in the request. No request ID`)                
        res.status(400).send("No request ID found.");
        return;
    }

    console.log(`[${requestId}] Receiving an order for a tasting menu. Looking for a cook...`)    
    if (!cook) {
        console.error(`[${requestId}] There is no cook available. No tip today from ${customerRequest?.customer}!`)
        res.status(404).send("No cook available");
        return;
    }
    console.log(`[${requestId}] Cook ${cook?.name} is available!`)    
    const postData = {
        waiter: waiter,
        requestId: requestId,
        cook: cook.name
    }
    axios.post("http://" + cook.ip + ":" + cook.port + "/operations/cook", postData)
        .then(agentResponse => {                
            console.log(`[${requestId}] Serving delicious tasting menu from ${cook?.name} to ${customerRequest?.customer}`);
            res.status(200).send(); return;
        })
        .catch(error => {
            console.error(`[${requestId}] Something went wrong: ${error}`);            
            res.status(400).send();
            return;
        });
}

function cook(req, res){
    const cook = process.env.HOSTNAME;    
    const waiterRequest = req.body;
    const requestId = waiterRequest?.requestId;
    console.log("REQUEST:", waiterRequest);
    
    if (!requestId) {
        console.log(`[N/A] Error in the request. No request ID`)                
        res.status(400).send("No request ID found.");
        return;
    }
    // Cook randomly goes crazy and does not serve anything.(20% of chance)
    console.log(`[${requestId}] Starting to prepare the requested tasting menu. Hope I won't go crazy...`)    
    const crazy = Math.random() < 0.2 
    if (crazy){
        console.log(`[${requestId}] Cook ${cook} is crazy at the moment. Cannot serve anything`);
        res.status(400).send("Cook went crazy. No food from him at the moment.");
        return;
    } else {
        console.log(`[${requestId}] Serving request to the waiter ${waiterRequest?.waiter}`);
        res.status(200).send(`Request ${requestId} delivered by cook ${cook}.`);
        return;
    }
}

function getAvailableAgent(agentType, agents){
    const matches = [];

    agents.forEach((value, key) => {
        if (key.startsWith(agentType)) {
            matches.push({
                ...value, 
                name: key
            });
        }
    })

    if (matches.length > 1) {
        const randomIndex = Math.floor(Math.random() * matches.length);
        return matches[randomIndex];
    }

    return matches[0] || null
}

function getAvailableCook(agents) {
    return getAvailableAgent("cook", agents);
}

function getAvailableWaiter(agents) {
    return getAvailableAgent("waiter", agents);
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
// operations
app.post("/operations/order", order);
app.post("/operations/request", request);
app.post("/operations/cook", cook);


app.listen(8080, () => console.log(`API for Observability Framework Demo at 8080!\nPrometheus endpoint at 8081`))

module.exports = { getAvailableCook, getAvailableWaiter };
