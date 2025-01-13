package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"sync"

	"github.com/go-chi/chi/v5"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	metricOrigin    = "src"
	prometheusPort  = 8081
	httpPort        = 8080
	metricsRegistry = prometheus.NewRegistry()
	metrics         = make(map[string]prometheus.Gauge)
	agentRegistry   = sync.Map{}
	metricMutex     sync.Mutex
)

func main() {
	r := chi.NewRouter()
	initializePrometheus()

	r.Get("/", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("API Metrics management"))
	})

	r.Route("/metrics", func(r chi.Router) {
		r.Get("/", getAllMetrics)
		r.Get("/{metricName}", getMetric)
		r.Post("/{metricName}", postMetric)
		r.Put("/{metricName}", putMetric)
		r.Delete("/{metricName}", deleteMetric)
	})

	r.Route("/agents", func(r chi.Router) {
		r.Get("/", getRegisteredAgents)
		r.Post("/{agentId}", postAgent)
		r.Delete("/{agentId}", deleteAgent)
	})

	r.Post("/kick", kick)

	log.Printf("Starting HTTP API on port %d\n", httpPort)
	go func() {
		log.Fatal(http.ListenAndServe(fmt.Sprintf(":%d", httpPort), r))
	}()

	http.Handle("/metrics", promhttp.HandlerFor(metricsRegistry, promhttp.HandlerOpts{}))
	log.Printf("Starting Prometheus metrics on port %d\n", prometheusPort)
	log.Fatal(http.ListenAndServe(fmt.Sprintf(":%d", prometheusPort), nil))
}

func initializePrometheus() {
	log.Printf("Environment: %s", metricOrigin)
}

func getAllMetrics(w http.ResponseWriter, r *http.Request) {
	var results []map[string]string
	metricMutex.Lock()
	for name, metric := range metrics {
		results = append(results, map[string]string{"name": name, "value": fmt.Sprintf("%v", metric)})
	}
	metricMutex.Unlock()
	json.NewEncoder(w).Encode(results)
}

func postMetric(w http.ResponseWriter, r *http.Request) {
	metricName := chi.URLParam(r, "metricName")
	metricMutex.Lock()
	defer metricMutex.Unlock()

	if _, exists := metrics[metricName]; exists {
		http.Error(w, "Metric already exists", http.StatusConflict)
		return
	}

	gauge := prometheus.NewGauge(prometheus.GaugeOpts{
		Name:        metricName,
		Help:        "Metric " + metricName,
		ConstLabels: prometheus.Labels{"metricOrigin": metricOrigin},
	})

	metrics[metricName] = gauge
	metricsRegistry.MustRegister(gauge)
	gauge.Set(0)
	w.WriteHeader(http.StatusCreated)
	w.Write([]byte("Metric created"))
}

func putMetric(w http.ResponseWriter, r *http.Request) {
	metricName := chi.URLParam(r, "metricName")
	value := r.URL.Query().Get("value")

	metricMutex.Lock()
	defer metricMutex.Unlock()

	if gauge, exists := metrics[metricName]; exists {
		convertedValue, err := strconv.ParseFloat(value, 64)
		if err != nil {
			gauge.Set(convertedValue)
			w.WriteHeader(http.StatusOK)
		}
		return
	}

	http.Error(w, "Metric not found", http.StatusNotFound)
}

// More handler functions like deleteMetric, getRegisteredAgents, postAgent, deleteAgent, kick
// would be similarly implemented using the chi router and Prometheus client.

func getMetric(w http.ResponseWriter, r *http.Request) {

}

func deleteMetric(w http.ResponseWriter, r *http.Request) {

}

func getRegisteredAgents(w http.ResponseWriter, r *http.Request) {

}

func postAgent(w http.ResponseWriter, r *http.Request) {

}

func deleteAgent(w http.ResponseWriter, r *http.Request) {

}

func kick(w http.ResponseWriter, r *http.Request) {

}
