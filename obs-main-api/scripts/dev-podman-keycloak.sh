SCRIPT_DIR="$(realpath "$(dirname "$0")")"
export CERT_FOLDER=$SCRIPT_DIR/certs

podman run -d --name keycloak-local \
  -p 8443:8443 \
  -v "$CERT_FOLDER:/opt/keycloak/certs:Z" \
  -v "$SCRIPT_DIR/import:/opt/keycloak/data/import:Z" \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=admin \
  -e KC_HTTPS_CERTIFICATE_FILE=/opt/keycloak/certs/keycloak.crt \
  -e KC_HTTPS_CERTIFICATE_KEY_FILE=/opt/keycloak/certs/keycloak.key \
  quay.io/keycloak/keycloak:latest \
  start-dev --import-realm

  echo CSA realm admin password: 9Hzg3p6z43yT+HBzNzM0Eg==