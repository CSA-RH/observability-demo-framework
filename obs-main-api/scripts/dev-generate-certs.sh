#!/usr/bin/env bash
# Create a directory for certificates
SCRIPT_DIR="$(realpath "$(dirname "$0")")"
export CERT_FOLDER=$SCRIPT_DIR/certs
mkdir -p $CERT_FOLDER

echo "1. Generating Private Root CA..."
openssl genrsa -out $CERT_FOLDER/rootCA.key 4096
# Se añaden las extensiones críticas para que Python reconozca este archivo como una CA válida
openssl req -x509 -new -nodes -key $CERT_FOLDER/rootCA.key -sha256 -days 1024 \
  -out $CERT_FOLDER/rootCA.crt \
  -subj "/CN=LocalMock-Root-CA" \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign,cRLSign"

echo "2. Generating Keycloak Private Key & CSR..."
openssl genrsa -out $CERT_FOLDER/keycloak.key 2048
openssl req -new -key $CERT_FOLDER/keycloak.key -out $CERT_FOLDER/keycloak.csr \
  -subj "/CN=localhost"

echo "3. Creating SAN extension configuration..."
cat <<EOF > $CERT_FOLDER/keycloak.ext
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = keycloak
IP.1 = 127.0.0.1
EOF

echo "4. Signing Keycloak Certificate with Local Root CA..."
openssl x509 -req -in $CERT_FOLDER/keycloak.csr -CA $CERT_FOLDER/rootCA.crt -CAkey $CERT_FOLDER/rootCA.key \
  -CAcreateserial -out $CERT_FOLDER/keycloak.crt -days 365 -sha256 -extfile $CERT_FOLDER/keycloak.ext

echo "✅ Done! Certificates generated in $CERT_FOLDER"