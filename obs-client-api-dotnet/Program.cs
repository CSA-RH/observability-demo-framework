using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Prometheus;

var builder = WebApplication.CreateBuilder(args);

// Add services for the REST API
builder.Services.AddControllers();
// Register IHttpClientFactory
builder.Services.AddHttpClient();

var app = builder.Build();

// Define the REST API to run on port 8080
app.Urls.Add("http://0.0.0.0:8080");

// Enable routing and map the REST API endpoints
app.UseRouting();
app.MapControllers();
app.MapMetrics();

app.Logger.LogInformation("Starting metrics server");
// Start a separate Prometheus metrics server on port 8081
var metricServer = new KestrelMetricServer(port: 8081);
metricServer.Start();


// Run the application
app.Run();
