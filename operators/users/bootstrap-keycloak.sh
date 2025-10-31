#!/bin/bash
set -e
set -o pipefail

# Load environment
# source ../env.sh
# Using NAMESPACE from env.sh, or providing a default
NAMESPACE=${NAMESPACE:-"obs-demo"}
echo "Using namespace: $NAMESPACE"

# --- 1. Define Variables ---

# ---!! SET YOUR TARGET REALM HERE !! ---
# All operations will be performed on this realm.
# It will be created if it does not exist.
PRIMARY_REALM="csa2"
# -----------------------------------------

KEYCLOAK_URL="https://$(oc get route -n $NAMESPACE --selector app=keycloak -ojsonpath='{.items[0].spec.host}')"
TEMP_ADMIN_USER=$(oc get secret idp-server-initial-admin -n $NAMESPACE -ojsonpath='{.data.username}' | base64 -d)
TEMP_ADMIN_PASS=$(oc get secret idp-server-initial-admin -n $NAMESPACE -ojsonpath='{.data.password}' | base64 -d)

# Vars for Automation Service Account (in $PRIMARY_REALM)
SERVICE_CLIENT_ID="automation-client"
AUTOMATION_CLIENT_CM="idp-data" # ConfigMap name

# Vars for Portal Admin User (in $PRIMARY_REALM)
PORTAL_REALM_GROUP="obs-demo-users"
PORTAL_ADMIN_USER="admin"
PORTAL_ADMIN_ROLE="obs-admin"
PORTAL_ADMIN_ROLE_DESC="Observability Demo Framework administrator role for Portal Management"
PORTAL_ADMIN_SECRET="obs-demo-admin-creds" # K8s Secret name


# --- 2. Get Admin Token ---
echo "--- Starting Keycloak Bootstrap ---"
echo "Logging in as '$TEMP_ADMIN_USER' to 'master' realm..."
ADMIN_TOKEN=$(curl -s -k -X POST \
  "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$TEMP_ADMIN_USER" \
  -d "password=$TEMP_ADMIN_PASS" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | jq -r .access_token)

if [ -z "$ADMIN_TOKEN" ] || [ "$ADMIN_TOKEN" == "null" ]; then
    echo "ERROR: Failed to get admin token. Check URL and credentials." >&2
    exit 1
fi
echo "Successfully logged in."

# --- 3. Idempotent Realm Creation ---
echo "--- Processing realm '$PRIMARY_REALM' ---"
echo "Checking for realm '$PRIMARY_REALM'..."
REALM_EXISTS=$(curl -s -k -o /dev/null -w "%{http_code}" \
  "$KEYCLOAK_URL/realms/$PRIMARY_REALM" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

if [ "$REALM_EXISTS" == "404" ]; then
  echo "Realm '$PRIMARY_REALM' not found. Creating..."
  curl -s -k -X POST "$KEYCLOAK_URL/admin/realms" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"realm": "'"$PRIMARY_REALM"'", "enabled": true}'
  echo "Realm '$PRIMARY_REALM' created."
else
  echo "Realm '$PRIMARY_REALM' already exists."
fi


# --- 4. Setup for '$PRIMARY_REALM' (Automation Client) ---
echo "--- Configuring '$SERVICE_CLIENT_ID' in realm '$PRIMARY_REALM' ---"

# 4.1. Check for/Create Service Account Client
echo "Checking for existing client '$SERVICE_CLIENT_ID'..."
CLIENT_UUID=$(curl -s -k -X GET \
  "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/clients?clientId=$SERVICE_CLIENT_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[0].id')

if [ "$CLIENT_UUID" == "null" ] || [ -z "$CLIENT_UUID" ]; then
  echo "Client not found. Creating '$SERVICE_CLIENT_ID'..."
  
  LOCATION_HEADER=$(curl -s -k -i -X POST \
    "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/clients" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "clientId": "'"$SERVICE_CLIENT_ID"'",
          "serviceAccountsEnabled": true,
          "clientAuthenticatorType": "client-secret",
          "publicClient": false,
          "standardFlowEnabled": false,
          "directAccessGrantsEnabled": false
        }' | grep -i 'Location:')
  
  CLIENT_UUID=$(echo "$LOCATION_HEADER" | awk -F'/' '{print $NF}' | tr -d '\r')
  
  if [ -z "$CLIENT_UUID" ]; then
    echo "ERROR: Failed to create client '$SERVICE_CLIENT_ID'." >&2
    exit 1
  fi
  echo "Client created with UUID: $CLIENT_UUID"
else
  echo "Client '$SERVICE_CLIENT_ID' already exists. Using UUID: $CLIENT_UUID"
fi

# 4.2. Assign Admin Roles
SERVICE_ACCOUNT_USER_ID=$(curl -s -k -X GET \
  "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/clients/$CLIENT_UUID/service-account-user" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r .id)

REALM_MGMT_CLIENT_UUID=$(curl -s -k -X GET \
  "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/clients?clientId=realm-management" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[0].id')

echo "Checking for 'manage-users' role..."
if curl -s -k -X GET \
  "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/users/$SERVICE_ACCOUNT_USER_ID/role-mappings/clients/$REALM_MGMT_CLIENT_UUID/effective" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[]' | grep -q 'manage-users'; then
  
  echo "Admin roles are already assigned."
else
  echo "Roles not assigned. Assigning all available admin roles..."
  ALL_ADMIN_ROLES_JSON=$(curl -s -k -X GET \
    "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/clients/$REALM_MGMT_CLIENT_UUID/roles" \
    -H "Authorization: Bearer $ADMIN_TOKEN")

  curl -s -k -X POST \
    "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/users/$SERVICE_ACCOUNT_USER_ID/role-mappings/clients/$REALM_MGMT_CLIENT_UUID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$ALL_ADMIN_ROLES_JSON" > /dev/null
  echo "All admin roles assigned."
fi

# 4.3. Retrieve and Create ConfigMap
echo "Retrieving secret for '$SERVICE_CLIENT_ID'..."
CLIENT_SECRET=$(curl -s -k -X GET \
  "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/clients/$CLIENT_UUID/client-secret" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r .value)

echo "Creating ConfigMap '$AUTOMATION_CLIENT_CM' in namespace '$NAMESPACE'..."
cat <<EOF | oc apply -n $NAMESPACE -f -
apiVersion: v1
data:
  client_id: $SERVICE_CLIENT_ID
  client_secret: $CLIENT_SECRET
  endpoint: $KEYCLOAK_URL
  realm: $PRIMARY_REALM
kind: ConfigMap
metadata:
  labels:
    observability-demo-framework: idp
  name: $AUTOMATION_CLIENT_CM
EOF


# --- 5. Setup for '$PRIMARY_REALM' (Portal Admin User) ---
echo "--- Configuring Portal Admin User in realm '$PRIMARY_REALM' ---"

# 5.1. Idempotent Group Creation
echo "Checking for group '$PORTAL_REALM_GROUP'..."
GROUP_EXISTS=$(curl -s -k -X GET \
  "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/groups?search=$PORTAL_REALM_GROUP" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[0].name')

if [ "$GROUP_EXISTS" == "$PORTAL_REALM_GROUP" ]; then
  echo "Group '$PORTAL_REALM_GROUP' already exists."
else
  echo "Group '$PORTAL_REALM_GROUP' not found. Creating..."
  curl -s -k -X POST "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/groups" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name": "'"$PORTAL_REALM_GROUP"'"}' > /dev/null
  echo "Group '$PORTAL_REALM_GROUP' created."
fi

# 5.2. Idempotent Role Creation
echo "Checking for role '$PORTAL_ADMIN_ROLE'..."
ROLE_EXISTS=$(curl -s -k -o /dev/null -w "%{http_code}" \
  "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/roles/$PORTAL_ADMIN_ROLE" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

if [ "$ROLE_EXISTS" == "404" ]; then
  echo "Role '$PORTAL_ADMIN_ROLE' not found. Creating..."
  curl -s -k -X POST "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/roles" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
          "name": "'"$PORTAL_ADMIN_ROLE"'",
          "description": "'"$PORTAL_ADMIN_ROLE_DESC"'"
        }' > /dev/null
  echo "Role '$PORTAL_ADMIN_ROLE' created."
else
  echo "Role '$PORTAL_ADMIN_ROLE' already exists."
fi

# 5.3. Idempotent User & K8s Secret Creation
# We use the K8s secret as the source of truth. If it exists, we assume the user is also correct.
echo "Checking for K8s secret '$PORTAL_ADMIN_SECRET' in namespace '$NAMESPACE'..."
if oc get secret $PORTAL_ADMIN_SECRET -n $NAMESPACE > /dev/null 2>&1; then
  echo "Secret '$PORTAL_ADMIN_SECRET' already exists. Assuming user '$PORTAL_ADMIN_USER' is configured."
else
  echo "Secret '$PORTAL_ADMIN_SECRET' not found. Creating user and secret..."
  NEW_ADMIN_PASS=$(openssl rand -base64 16 | tr -d '\n')
  
  # Check if user exists
  USER_ID=$(curl -s -k -X GET \
    "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/users?username=$PORTAL_ADMIN_USER" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[0].id')

  if [ "$USER_ID" == "null" ] || [ -z "$USER_ID" ]; then
    echo "User '$PORTAL_ADMIN_USER' not found. Creating..."
    curl -s -k -X POST "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/users" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
            "username": "'"$PORTAL_ADMIN_USER"'",
            "enabled": true,
            "credentials": [
              {
                "type": "password",
                "value": "'"$NEW_ADMIN_PASS"'",
                "temporary": false
              }
            ]
          }' > /dev/null
    echo "User '$PORTAL_ADMIN_USER' created."
  else
    echo "User '$PORTAL_ADMIN_USER' already exists. Resetting password..."
    curl -s -k -X PUT "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/users/$USER_ID/reset-password" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
            "type": "password",
            "value": "'"$NEW_ADMIN_PASS"'",
            "temporary": false
          }' > /dev/null
    echo "Password for user '$PORTAL_ADMIN_USER' reset."
  fi
  
  # Create the K8s secret
  oc create secret generic $PORTAL_ADMIN_SECRET -n $NAMESPACE \
    --from-literal=username=$PORTAL_ADMIN_USER \
    --from-literal=password=$NEW_ADMIN_PASS
  echo "K8s secret '$PORTAL_ADMIN_SECRET' created."
fi

# 5.4. Idempotent Role Assignment
echo "Assigning role '$PORTAL_ADMIN_ROLE' to user '$PORTAL_ADMIN_USER'..."
# Get User UUID
USER_ID=$(curl -s -k -X GET \
  "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/users?username=$PORTAL_ADMIN_USER" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[0].id')

if [ -z "$USER_ID" ] || [ "$USER_ID" == "null" ]; then
  echo "ERROR: Could not find user '$PORTAL_ADMIN_USER' to assign role." >&2
  exit 1
fi

# Check if role is already assigned.
# We must wrap the grep check in an 'if' statement.
# 'set -e' will exit the script if grep returns 1 (not found),
# unless it's part of a conditional test like this.
if curl -s -k -X GET \
  "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/users/$USER_ID/role-mappings/realm/effective" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.[]' | grep -q "^$PORTAL_ADMIN_ROLE$"; then

  echo "Role '$PORTAL_ADMIN_ROLE' is already assigned to user '$PORTAL_ADMIN_USER'."
else
  # grep returned 1 (not found), so we must assign the role.
  echo "Role not assigned. Assigning..."
  
  # Get the full role object to assign
  ROLE_JSON_FOR_ASSIGNMENT=$(curl -s -k -X GET \
    "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/roles/$PORTAL_ADMIN_ROLE" \
    -H "Authorization: Bearer $ADMIN_TOKEN")

  curl -s -k -X POST "$KEYCLOAK_URL/admin/realms/$PRIMARY_REALM/users/$USER_ID/role-mappings/realm" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "[ $ROLE_JSON_FOR_ASSIGNMENT ]" > /dev/null
  echo "Successfully assigned role '$PORTAL_ADMIN_ROLE' to user '$PORTAL_ADMIN_USER'."
fi


echo ""
echo "--- ✅ All Keycloak Bootstrapping Complete for realm '$PRIMARY_REALM'! ---"
echo ""
echo "Automation client for '$PRIMARY_REALM' realm (in ConfigMap '$AUTOMATION_CLIENT_CM'):"
echo "  CLIENT_ID: $SERVICE_CLIENT_ID"
echo "  CLIENT_SECRET: [$(echo $CLIENT_SECRET | head -c 4)...]"
echo ""
echo "Admin user for '$PRIMARY_REALM' realm (in Secret '$PORTAL_ADMIN_SECRET'):"
echo "  USERNAME: $PORTAL_ADMIN_USER"
echo "  PASSWORD: [stored in secret]"
echo "----------------------------------------------------"