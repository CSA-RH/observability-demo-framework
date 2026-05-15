"use strict";

const express = require('express');
const axios = require('axios');
const api = require('@opentelemetry/api');
const crypto = require('crypto'); 
const { MeterRegistry } = require('@opentelemetry/metrics');
const { PrometheusExporter } = require('@opentelemetry/exporter-prometheus');

// 1. Initialize Pino with the OTel Mixin
// This ensures TraceId/SpanId are injected into every log in PascalCase (matching .NET)
const logger = require('pino')({
    formatters: {
        log(object) {
            // The OTel agent has already injected trace_id/span_id into 'object'
            // We simply rename them to PascalCase and delete the snake_case versions
            if (object.trace_id) {
                object.TraceId = object.trace_id;
                delete object.trace_id;
            }
            if (object.span_id) {
                object.SpanId = object.span_id;
                delete object.span_id;
            }
            
            // Optional: Clean up other OTel-injected fields if they clutter your logs
            delete object.trace_flags; 
            
            return object; // Return the sanitized object
        }
    }
});

// 2. Override console methods to use Pino
// Now console.log() automatically produces single-line JSON with Trace context
console.log = (...args) => logger.info(...args);
console.error = (...args) => logger.error(...args);

/** * NOTE: Manual LoggerProvider and OTLPLogExporter are removed. 
 * The OTel Operator handles the SDK, and Vector/Loki handles the collection 
 * via stdout, making the app code much lighter.
 */

const metricOrigin = "src";
const prometheusPort = 8081;
const app = express();

var _dict = {};
var _meter = {};
var _labels = {};
const _agents = new Map();

function initializePrometheusEndpoint() {
    _meter = new MeterRegistry().getMeter('example-prometheus');
    const exporter = new PrometheusExporter(
        {
            startServer: true,
            port: prometheusPort
        },
        () => {
            console.log(`prometheus scrape endpoint: http://0.0.0.0:${prometheusPort}/metrics`);
        }
    );
    _meter.addExporter(exporter);
    _labels = _meter.labels({ metricOrigin: metricOrigin });
    _dict = {};
}

// --- Metrics Handlers ---
function getAllMetrics(req, res) {
    var results = [];
    for (var metricName in _dict) {
        const result = {
            name: metricName,
            value: _dict[metricName].bind(_labels)._data.toString()
        };
        results.push(result);
    }
    res.status(200).send(JSON.stringify(results));
}

function getMetric(req, res) {
    const metricName = req.params.metricName;
    if (metricName in _dict) {
        res.status(200).send(_dict[metricName].bind(_labels)._data.toString());
    } else {
        res.status(404).send("Not found");
    }
}

function postMetric(req, res) {
    const metricName = req.params.metricName;
    const value = parseInt(req.query.value);
    if (metricName in _dict) {
        res.status(409).send(`Cannot create metric ${metricName}. Already created`);
    } else {
        const newMetric = _meter.createGauge(metricName, {
            monotonic: false,
            labelKeys: ["metricOrigin"],
            description: `Metric ${metricName}`
        });
        newMetric.bind(_labels).set(value);
        _dict[metricName] = newMetric;
        res.status(200).send(`Created metric ${metricName} with value ${value}`);
    }
}

function putMetric(req, res) {
    const metricName = req.params.metricName;
    const value = parseInt(req.query.value);
    if (metricName in _dict) {
        _dict[metricName].bind(_labels).set(value);
        res.status(200).send(`Modified metric ${metricName} with value ${value}`);
    } else {
        res.status(404).send(`Cannot modify metric ${metricName}. Not found`);
    }
}

function deleteMetric(req, res) {
    initializePrometheusEndpoint();
    res.status(200).send("Delete operation too destructive");
}

// --- Agent Management ---
function getRegisteredAgents(req, res) {
    res.status(200).send(JSON.stringify(Object.fromEntries(_agents)));
}

function postAgent(req, res) {
    const agentId = req.params.agentId;
    const { ip, port } = req.body;
    if (!ip || !port) {
        res.status(400).send("Valid IP and Port required.");
        return;
    }
    _agents.set(agentId, { ip, port });
    res.status(200).send();
}

function deleteAgent(req, res) {
    _agents.delete(req.params.agentId);
    res.status(200).send();
}

// --- Operation Handlers (Business Logic) ---
function order(req, res) {
    const customer = process.env.HOSTNAME;
    const requestId = crypto.randomUUID(); 
    const waiter = getAvailableWaiter(_agents);
    
    console.log(`[${requestId}] Ordering a tasting menu...`);    
    if (!waiter) {
        console.error(`[${requestId}] There is no waiter available.`);
        res.status(404).send("No waiter available");
        return;
    }

    const postData = { customer, requestId, waiter: waiter.name };
    axios.post(`http://${waiter.ip}:${waiter.port}/operations/request`, postData)
        .then(() => {                
            console.log(`[${requestId}] It was soooo good!`);            
            res.status(200).send();
        })
        .catch(error => {
            console.error(`[${requestId}] Error: ${error.message}`);            
            res.status(400).send();
        });
}

function request(req, res){
    const waiter = process.env.HOSTNAME;
    const cook = getAvailableCook(_agents);
    const { requestId, customer } = req.body;

    if (!requestId) {
        console.error("[N/A] Error: No request ID found.");
        res.status(400).send("No request ID found.");
        return;
    }

    console.log(`[${requestId}] Looking for a cook...`);    
    if (!cook) {
        console.error(`[${requestId}] No cook available for ${customer}`);
        res.status(404).send("No cook available");
        return;
    }

    const postData = { waiter, requestId, cook: cook.name };
    axios.post(`http://${cook.ip}:${cook.port}/operations/cook`, postData)
        .then(() => {                
            console.log(`[${requestId}] Serving menu from ${cook.name} to ${customer}`);
            res.status(200).send();
        })
        .catch(error => {
            console.error(`[${requestId}] Error: ${error.message}`);            
            res.status(400).send();
        });
}

function cook(req, res){
    const cookName = process.env.HOSTNAME;    
    const { requestId, waiter } = req.body;
    
    if (!requestId) {
        console.error("[N/A] Error: No request ID");
        res.status(400).send("No request ID found.");
        return;
    }

    const crazy = Math.random() < 0.2; 
    if (crazy){
        console.log(`[${requestId}] Cook ${cookName} went crazy!`);
        res.status(400).send("Cook went crazy.");
    } else {
        console.log(`[${requestId}] Delivering to waiter ${waiter}`);
        res.status(200).send(`Request ${requestId} delivered.`);
    }
}

// --- Helpers ---
function getAvailableAgent(agentType, agents) {
    const matches = [];
    agents.forEach((value, key) => {
        if (key.startsWith(agentType)) {
            matches.push({ ...value, name: key });
        }
    });
    return matches.length > 0 ? matches[Math.floor(Math.random() * matches.length)] : null;
}

const getAvailableCook = (agents) => getAvailableAgent("cook", agents);
const getAvailableWaiter = (agents) => getAvailableAgent("waiter", agents);

// --- App Startup ---
initializePrometheusEndpoint();
app.use(express.json());

app.get('/', (req, res) => res.status(200).send("API Metrics management"));
app.get("/metrics", getAllMetrics);
app.get("/metrics/:metricName", getMetric);
app.post("/metrics/:metricName", postMetric);
app.put("/metrics/:metricName", putMetric);
app.delete("/metrics/:metricName", deleteMetric);
app.get("/agents", getRegisteredAgents);
app.post("/agents/:agentId", postAgent);
app.delete("/agents/:agentId", deleteAgent);
app.post("/operations/order", order);
app.post("/operations/request", request);
app.post("/operations/cook", cook);

app.listen(8080, () => {
    console.log("API for Observability Framework Demo at 8080!\nPrometheus endpoint at 8081");
});

module.exports = { getAvailableCook, getAvailableWaiter };