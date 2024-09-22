import http.client
import json
import socket

#Call IP 
source_agent_ip="10.128.2.124"
target_agent_ip="10.128.2.126"
targetName="sergio-paulo-barbara-santos-duda"	
print(f"Calling POST http://{source_agent_ip}:8080/agents/{targetName} with destination ip {target_agent_ip}")
next_hop_address = {
    "ip": target_agent_ip,
    "port": 8080
}
json_next_hop_address = json.dumps(next_hop_address)
try:
    print("http://" + source_agent_ip + ":8080")
    conn = http.client.HTTPConnection(source_agent_ip, 8080, timeout=2)
    headers = {
        'Content-Type': 'application/json'
    }
    # Make the POST request, attaching the JSON body
    conn.request("POST", "/agents/" + targetName, body=json_next_hop_address, headers=headers)
    # Get the response
    response = conn.getresponse()
    data = response.read()

    # Print the response data
    print(data.decode("utf-8"))
except socket.timeout:
    print("The request timed out.")

except Exception as e:
    # Handle other possible exceptions
    print(f"Request failed: {e}")

finally:
    # Close the connection
    conn.close()
