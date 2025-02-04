using Microsoft.AspNetCore.Mvc;
using System.Collections.Concurrent;
using Prometheus;
using System.Text;
using System.Text.Json;

public class KickRequest
{
    public int? Count { get; set; }
    public string? Sender { get; set; }
}

public class AgentData
{
    public string? Ip { get; set; }
    public int Port { get; set; }
    public string? Name {get; set;}
}

public class CustomerRequest
{
    public string RequestId { get; set; } = string.Empty;
    public string Customer { get; set; } = string.Empty;
}

[Route("")]
[ApiController]
public class ApiController : ControllerBase
{
    private static readonly ConcurrentDictionary<string, Gauge> _metrics = new();
    private static readonly Dictionary<string, AgentData> _agents = new();
    private readonly IHttpClientFactory _httpClientFactory;
    private readonly ILogger<ApiController> _logger;



    
    public ApiController(IHttpClientFactory httpClientFactory, ILogger<ApiController> logger)
    {
        _httpClientFactory = httpClientFactory;
        _logger = logger;
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
        agentData.Name = agentName;

        // Return a success message with the agent name and IP.
        return Ok();
    }

    // GET /agents
    [HttpGet("agents")]
    public IActionResult GetAllAgents()
    {
        return Ok(_agents);
    }

    public static AgentData? GetAvailableAgent(string agentType, Dictionary<string, AgentData> agents)
    {
        var matches = agents
            .Where(kv => kv.Key.StartsWith(agentType, StringComparison.OrdinalIgnoreCase))
            .Select(kv => new AgentData
            {
                Name = kv.Key,
                Ip = kv.Value.Ip,
                Port = kv.Value.Port
            })
            .ToList();

        if (matches.Count > 1)
        {
            var random = new Random();
            return matches[random.Next(matches.Count)];
        }

        return matches.FirstOrDefault();
    }

    public static AgentData? GetAvailableCook()
    {
        return GetAvailableAgent("cook", _agents);
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

    [HttpPost("operations/request")]
    public async Task<IActionResult> RequestOperation([FromBody] CustomerRequest customerRequest)
    {
        var waiter = Environment.GetEnvironmentVariable("HOSTNAME");

        if (customerRequest == null || string.IsNullOrEmpty(customerRequest.RequestId))
        {
            _logger.LogError("[N/A] Error in the request. No request ID");
            return BadRequest("No request ID found.");
        }

        string requestId = customerRequest.RequestId;
        _logger.LogInformation($"[{requestId}] Receiving an order for a tasting menu. Looking for a cook...");

        var cook = GetAvailableCook();
        if (cook == null)
        {
            _logger.LogError($"[{requestId}] There is no cook available. No tip today from {customerRequest.Customer}!");
            return NotFound("No cook available");
        }

        _logger.LogInformation($"[{requestId}] Cook {cook.Name} is available!");

        var postData = new
        {
            waiter = waiter,
            requestId = requestId,
            cook = cook.Name
        };

        
        var cookUrl = $"http://{cook.Ip}:{cook.Port}/operations/cook";

        try
        {
            var client = _httpClientFactory.CreateClient();
            var cts = new CancellationTokenSource(TimeSpan.FromSeconds(2));            
            var response = await client.PostAsJsonAsync(cookUrl, postData, cts.Token);
            if (response.IsSuccessStatusCode)
            {
                _logger.LogInformation($"[{requestId}] Serving delicious tasting menu from {cook.Name} to {customerRequest.Customer}");
                return Ok();
            }
            else
            {
                _logger.LogError($"[{requestId}] Cook service returned an error: {response.StatusCode}");
                return StatusCode((int)response.StatusCode);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError($"[{requestId}] Something went wrong: {ex.Message}");
            return StatusCode(500, "Internal Server Error");
        }
    }


    [HttpPost("kick")]
    public async Task<IActionResult> Kick([FromBody] KickRequest kickRequest)
    {
        int kickCount = kickRequest.Count ?? 3; // Default kickCount

        if (kickCount == 0)
        {
            _logger.LogInformation("no more kicks");
            return Ok();
        }

        string agentReceived = kickRequest.Sender ?? "INITIAL KICK";
        string sender = Environment.GetEnvironmentVariable("HOSTNAME") ?? "localhost";
        
        _logger.LogInformation("---");
        _logger.LogInformation($"Sent by {agentReceived}. Kicks remaining: {kickCount}");

        foreach (var (agentId, agentInfo) in _agents)
        {
            var post_data = new
            {
                sender,
                count = kickCount - 1
            };

            var agentRequestId = Guid.NewGuid().ToString();
            _logger.LogInformation($"[{agentRequestId}][REQUEST from {sender} to {agentId}]");

            try
            {
                var client = _httpClientFactory.CreateClient();
                var cts = new CancellationTokenSource(TimeSpan.FromSeconds(2));

                var response = await client.PostAsJsonAsync($"http://{agentInfo.Ip}:{agentInfo.Port}/kick", post_data, cts.Token);

                _logger.LogInformation($"[{agentRequestId}][RESPONSE from {agentId}]: Status = {response.StatusCode}");
            }
            catch (Exception ex)
            {
                _logger.LogError($"Error: {ex.Message}");
                return StatusCode(500);
            }
        }

        return Ok();
    }
}
