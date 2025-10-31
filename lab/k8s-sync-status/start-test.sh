#!/bin/bash

# --- Configuration ---
# Set the full URL for your API endpoint
STATUS_URL="http://127.0.0.1:8000/api/sync-status"
# ---------------------

echo "Starting poller. Press [Ctrl+C] to stop."
echo "Polling endpoint: $STATUS_URL"
echo "" # Newline for cleaner output

# This is an infinite loop
while true
do
    # 1. Perform the curl request
    # -s = silent mode (don't show progress bar)
    # -X GET = explicitly use the GET method
    result=$(curl -s -X GET "$STATUS_URL")
    
    # 2. Print the result
    # We add a timestamp for clarity
    echo "[$(date +'%T')] Status: $result"
    
    # 3. Wait for 3 seconds
    sleep 3
done