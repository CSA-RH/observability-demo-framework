import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Gauge;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.*;

import javax.annotation.PostConstruct;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@SpringBootApplication
public class ObservabilityDemoApplication {

    public static void main(String[] args) {
        SpringApplication.run(ObservabilityDemoApplication.class, args);
    }
}

@RestController
@RequestMapping("/metrics")
class MetricsController {

    private final Map<String, Gauge> metrics = new HashMap<>();
    private final MeterRegistry meterRegistry;
    private final Map<String, Agent> agents = new HashMap<>();

    @Autowired
    public MetricsController(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
    }

    @PostConstruct
    public void init() {
        System.out.println("Environment: src");
    }

    @PostMapping("/{metricName}")
    public String createMetric(@PathVariable String metricName, @RequestParam int value) {
        if (metrics.containsKey(metricName)) {
            return "Metric already exists";
        }

        Gauge gauge = Gauge.builder(metricName, value, val -> val)
            .description("Metric " + metricName)
            .tag("metricOrigin", "src")
            .register(meterRegistry);

        metrics.put(metricName, gauge);
        return "Metric created";
    }

    @GetMapping
    public Map<String, String> getAllMetrics() {
        Map<String, String> results = new HashMap<>();
        metrics.forEach((name, gauge) -> results.put(name, gauge.value()));
        return results;
    }

    @PutMapping("/{metricName}")
    public String updateMetric(@PathVariable String metricName, @RequestParam int value) {
        if (metrics.containsKey(metricName)) {
            Gauge gauge = metrics.get(metricName);
            gauge.value(value);
            return "Metric updated";
        }
        return "Metric not found";
    }

    // Similar methods for deleteMetric, registerAgent, deleteAgent, and kick
    // Implement kick using RestTemplate or WebClient for agent communication.
}

class Agent {
    private String ip;
    private int port;

    public Agent(String ip, int port) {
        this.ip = ip;
        this.port = port;
    }

    // Getters and setters...
}
