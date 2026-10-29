podman run -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=admin" \
  -e "MINIO_ROOT_PASSWORD=p455w0rd" \
  -v ./minio-data:/data \
  minio/minio server /data --console-address ":9001"