"use strict";

const express = require('express');
const axios = require('axios');
const crypto = require('crypto');
const http = require('http');
const client = require('prom-client');

// 1. Initialize Pino with the OTel Mixin
// This ensures TraceId/SpanId are injected into every log in PascalCase (matching .NET)
const logger = require('pino')({
    formatters: {
        log(object) {
            if (object.trace_id) {
                object.TraceId = object.trace_id;
                delete object.trace_id;
            }
            if (object.span_id) {
                object.SpanId = object.span_id;
                delete object.span_id;
            }
            delete object.trace_flags;
            return object;
        }
    }
});

console.log = (...args) => logger.info(...args);
console.error = (...args) => logger.error(...args);

const metricOrigin = "src";
const prometheusPort = 8081;
const app = express();

const register = new client.Registry();
var _dict = {};
var _prometheusServer = null;
const _agents = new Map();

function initializePrometheusEndpoint() {
    register.clear();
    _dict = {};

    if (_prometheusServer) {
        _prometheusServer.close();
        _prometheusServer = null;
    }

    _prometheusServer = http.createServer(async (req, res) => {
        res.setHeader('Content-Type', register.contentType);
        res.end(await register.metrics());
    });

    _prometheusServer.listen(prometheusPort, () => {
        console.log(`prometheus scrape endpoint: http://0.0.0.0:${prometheusPort}/metrics`);
    });
}

function initializeAgentTargets() {
    const targetEnv = process.env.TARGETS;

    if (!targetEnv || !targetEnv.trim()) {
        return;
    }

    targetEnv.split(',').forEach(id => {
        const trimmedId = id.trim();
        if (trimmedId) {
            _agents.set(trimmedId, { port: 8080 });
        }
    });
}

function parseMetricValue(rawValue) {
    const value = Number.parseInt(rawValue, 10);
    if (Number.isNaN(value)) {
        return null;
    }
    return value;
}

// --- Metrics Handlers ---
function getAllMetrics(req, res) {
    const results = [];
    for (const metricName in _dict) {
        results.push({
            name: metricName,
            value: String(_dict[metricName].value)
        });
    }
    res.status(200).send(JSON.stringify(results));
}

function getMetric(req, res) {
    const metricName = req.params.metricName;
    if (metricName in _dict) {
        res.status(200).send(String(_dict[metricName].value));
    } else {
        res.status(404).send("Not found");
    }
}

function postMetric(req, res) {
    const metricName = req.params.metricName;
    const value = parseMetricValue(req.query.value);

    if (value === null) {
        res.status(400).send("Invalid metric value");
        return;
    }

    if (metricName in _dict) {
        res.status(409).send(`Cannot create metric ${metricName}. Already created`);
        return;
    }

    try {
        const gauge = new client.Gauge({
            name: metricName,
            help: `Metric ${metricName}`,
            labelNames: ["metricOrigin"],
            registers: [register],
        });
        gauge.set({ metricOrigin }, value);
        _dict[metricName] = { gauge, value };
        res.status(200).send(`Created metric ${metricName} with value ${value}`);
    } catch (error) {
        console.error(`Failed to create metric ${metricName}: ${error.message}`);
        res.status(400).send(`Cannot create metric ${metricName}`);
    }
}

function putMetric(req, res) {
    const metricName = req.params.metricName;
    const value = parseMetricValue(req.query.value);

    if (value === null) {
        res.status(400).send("Invalid metric value");
        return;
    }

    if (metricName in _dict) {
        _dict[metricName].gauge.set({ metricOrigin }, value);
        _dict[metricName].value = value;
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
    const { dns, port } = req.body;
    if (!dns || !port) {
        res.status(400).send("Valid DNS and Port required.");
        return;
    }
    _agents.set(agentId, { dns, port });
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
    axios.post(`http://${waiter.name}:${waiter.port}/operations/request`, postData)
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
    axios.post(`http://${cook.name}:${cook.port}/operations/cook`, postData)
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
initializeAgentTargets();
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
