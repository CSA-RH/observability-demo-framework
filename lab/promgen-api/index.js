"use strict";

// imports
const express = require ('express')
const { MeterRegistry } = require('@opentelemetry/metrics');
const { PrometheusExporter } = require('@opentelemetry/exporter-prometheus');
const metricOrigin = "src"
console.log("Environment: " + metricOrigin);

// set up prometheus 
const prometheusPort = 8081;
const app = express();

var _dict = {}
var _meter = {}
var _labels = {}

function initializePrometheusEndpoint() {
    
    _meter = new MeterRegistry().getMeter('example-prometheus');
    const exporter = new PrometheusExporter(
      {
        startServer: true,
        port: prometheusPort
      },
      () => {
        console.log("prometheus scrape endpoint: http://localhost:"
          + prometheusPort 
          + "/metrics");
      }
    );
    _meter.addExporter(exporter);
    _labels = _meter.labels({ metricOrigin: metricOrigin});
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

function patchMetric(req, res) {
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

initializePrometheusEndpoint();

// ROUTES
app.get('/', (req, res) => {
    res.status(200).send("API Metrics management")
});
app.get("/metrics", getAllMetrics);
app.get("/metrics/:metricName", getMetric);
app.post("/metrics/:metricName", postMetric);
app.patch("/metrics/:metricName", patchMetric);
app.delete("/metrics/:metricName", deleteMetric);

app.listen(8080, () => console.log(`API for handling Prometheus metrics at 8080!\nPrometheus endpoint at 8081`))