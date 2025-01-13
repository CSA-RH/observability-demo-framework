using Microsoft.AspNetCore.Mvc;
using System.Collections.Concurrent;
using Prometheus;

public class KickRequest
{
    public int? Count { get; set; }
    public string? Sender { get; set; }
}

public class AgentData
{
    public string? Ip { get; set; }
    public int Port { get; set; }
}

[Route("")]
[ApiController]
public class ApiController : ControllerBase
{
    private static readonly ConcurrentDictionary<string, Gauge> _metrics = new();
    private static readonly Dictionary<string, AgentData> _agents = new();
    private readonly IHttpClientFactory _httpClientFactory;
    
    public ApiController(IHttpClientFactory httpClientFactory)
    {
        _httpClientFactory = httpClientFactory;
    }

    [HttpGet]
        [Route("")] // This defines the root level route
        public IActionResult GetRoot()
        {
            return Ok(); // Returns 200 OK
        }

    // POST /metrics/{metricname}
    [HttpPost("metrics/{metricname}")]
    public IActionResult CreateMetric(string metricname, [FromQuery] double value)
    {
        if (_metrics.ContainsKey(metricname))
            return Conflict($"Metric '{metricname}' already exists.");

        var gauge = Metrics.CreateGauge(metricname, "Custom gauge metric");
        gauge.Set(value);
        _metrics[metricname] = gauge;

        return Ok(new { Message = $"Metric '{metricname}' created." });
    }

    // GET /metrics
    [HttpGet("metrics")]
    public IActionResult GetAllMetrics()
    {
        return Ok(_metrics.Keys);
    }
    
    // GET /metrics/{metricname}
    [HttpGet("metrics/{metricname}")]
    public IActionResult GetMetric(string metricname)
    {
        if (!_metrics.ContainsKey(metricname))
            return NotFound($"Metric '{metricname}' not found.");

        var value = _metrics[metricname].Value;
        return Ok(new { Metric = metricname, Value = value });
    }


    // Put /metrics/{metricname}
    [HttpPut("metrics/{metricname}")]
    public IActionResult UpdateMetric(string metricname, [FromQuery] double value)
    {
        if (!_metrics.ContainsKey(metricname))
            return NotFound($"Metric '{metricname}' not found.");

        _metrics[metricname].Set(value);
        return Ok(new { Message = $"Metric '{metricname}' updated to {value}." });
    }

    [HttpPost("agents/{agentName}")]
    public IActionResult CreateAgent(string agentName, [FromBody] AgentData agentData)
    {
        if (string.IsNullOrEmpty(agentData.Ip) || agentData.Port == 0)
        {
            return BadRequest("Invalid agent data.");
        }

        // Store the agent data in the dictionary keyed by the IP.
        _agents[agentName] = agentData;

        // Return a success message with the agent name and IP.
        return Ok();
    }

    // GET /agents
    [HttpGet("agents")]
    public IActionResult GetAllAgents()
    {
        return Ok(_agents);
    }
    
    // DELETE method to remove an agent by IP.
    [HttpDelete("agents/{agentname}")]
    public IActionResult DeleteAgent(string agentname)
    {
        // Find the agent by agentname in _agents based on IP (assuming agentname is the IP here).
        if (_agents.ContainsKey(agentname))
        {
            // Remove the agent from the dictionary.
            _agents.Remove(agentname);
            return Ok(new { message = $"Agent with IP '{agentname}' has been deleted." });
        }
        else
        {
            return NotFound(new { message = $"Agent with IP '{agentname}' not found." });
        }
    }

    [HttpPost("kick")]
    public async Task<IActionResult> Kick([FromBody] KickRequest kickRequest)
    {
        int kickCount = kickRequest.Count ?? 3; // Default kickCount

        if (kickCount == 0)
        {
            Console.WriteLine("no more kicks");
            return Ok();
        }

        string agentReceived = kickRequest.Sender ?? "INITIAL KICK";
        string sender = Environment.GetEnvironmentVariable("HOSTNAME") ?? "localhost";
        
        Console.WriteLine("---");
        Console.WriteLine($"Sent by {agentReceived}. Kicks remaining: {kickCount}");

        foreach (var (agentId, agentInfo) in _agents)
        {
            var post_data = new
            {
                sender,
                count = kickCount - 1
            };

            var agentRequestId = Guid.NewGuid().ToString();
            Console.WriteLine($"[{agentRequestId}][REQUEST from {sender} to {agentId}]");

            try
            {
                var client = _httpClientFactory.CreateClient();
                var cts = new CancellationTokenSource(TimeSpan.FromSeconds(2));

                var response = await client.PostAsJsonAsync($"http://{agentInfo.Ip}:{agentInfo.Port}/kick", post_data, cts.Token);

                Console.WriteLine($"[{agentRequestId}][RESPONSE from {agentId}]: Status = {response.StatusCode}");
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Error: {ex.Message}");
                return StatusCode(500);
            }
        }

        return Ok();
    }
}
