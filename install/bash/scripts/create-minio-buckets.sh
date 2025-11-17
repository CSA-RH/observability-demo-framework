#!/bin/sh
set -eu

# Define a writeable config directory inside the container
CONFIG_DIR="/tmp/.mc"

# Use the --config-dir flag on ALL mc commands
echo "Using mc config directory: $CONFIG_DIR"
mc --config-dir $CONFIG_DIR --version

echo "Setting alias..."
mc --config-dir $CONFIG_DIR alias set obs-minio http://obs-minio.minio.svc:9000 minioadmin minioadmin123

echo "Listing buckets..."
mc --config-dir $CONFIG_DIR ls obs-minio

# Use --ignore-existing to make the script idempotent
echo "Creating buckets..."
mc --config-dir $CONFIG_DIR mb --ignore-existing obs-minio/loki-storage2
mc --config-dir $CONFIG_DIR mb --ignore-existing obs-minio/tempo-storage2

echo "✅ Minio buckets are ready."