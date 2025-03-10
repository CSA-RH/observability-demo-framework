# Install keycloak for local development. 
With podman, simply install Keycloak locally with the following command:  

```bash
podman run -d \
    --name keycloak-dev \
    -p 8080:8080 -p 8443:8443 -p 9000:9000 \
    -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
    -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin \
    quay.io/keycloak/keycloak:26.0.6 start-dev
```

Login to the instance at http://localhost:8080 and introduce `admin`/`admin` as user/password

To create the csa realm, simply click on the master realm dropdown box and click "Create realm". In the next window, click on "Browse" to select the csa realm json file `realm-csa-local.json`. Make sure that the flag Enabled is set to "On". Once loaded, the realm name and json information will be displayed. Click on Create and add some users once the csa realm is selected. 

# Install Keycloak in the cluster. 
## Install Operator 

```bash
cat <<EOF | oc apply -f - 
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  annotations:
    olm.providedAPIs: Keycloak.v2alpha1.k8s.keycloak.org,KeycloakRealmImport.v2alpha1.k8s.keycloak.org  
  name: keycloak-operator-group  
spec:
  targetNamespaces:
  - $(oc project -q)
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  labels:
    operators.coreos.com/rhbk-operator.keycloak: ""
  name: rhbk-operator  
spec:
  channel: stable-v26.0
  installPlanApproval: Automatic
  name: rhbk-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
  startingCSV: rhbk-operator.v26.0.8-opr.1
EOF
```

## Install postgres database for realm information storage

```bash
cat <<EOF | oc create -f -
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgresql-db
  labels: 
    observability-demo-framework: idp
spec:
  serviceName: postgresql-db-service
  selector:
    matchLabels:
      app: postgresql-db
  replicas: 1
  template:
    metadata:
      labels:
        app: postgresql-db
    spec:
      containers:
        - name: postgresql-db
          image: postgres:15
          volumeMounts:
            - mountPath: /data
              name: cache-volume
          env:
            - name: POSTGRES_USER
              value: testuser
            - name: POSTGRES_PASSWORD
              value: testpassword
            - name: PGDATA
              value: /data/pgdata
            - name: POSTGRES_DB
              value: keycloak
      volumes:
        - name: cache-volume
          emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-db
  labels: 
    observability-demo-framework: idp
spec:
  selector:
    app: postgresql-db
  type: ClusterIP
  ports:
  - port: 5432
    targetPort: 5432
---
# --- Create database secret ---
apiVersion: v1
kind: Secret
metadata:
  name: keycloak-database-secret
  labels: 
    observability-demo-framework: idp
type: Opaque
data:
  password: dGVzdHBhc3N3b3Jk
  username: dGVzdHVzZXI=
EOF
```

## Create keycloak instance.

### Create private CA in a secret 

```bash
## Regenerate output folder
PROJECT_NAME=$(oc project -q)

rm -rf ./output
mkdir output

PRIVATE_CA_KEY=./output/privateCA.key
PRIVATE_CA_PEM=./output/privateCA.pem
## Create Private CA key
openssl genrsa -out ${PRIVATE_CA_KEY} 2048 
## Create Private CA Root Certificate
openssl req -x509 -new -nodes -key ${PRIVATE_CA_KEY} -sha256 -days 1825 -out ${PRIVATE_CA_PEM} \
    -subj "/C=ES/ST=Caribe/L=Macondo/O=ACME/OU=CSA/CN=PrivateCA for custom Certificates (Keycloak Demo)"

# --- Create Keycloak route certificate --- 
CERT_KEY=./output/cert.key
CERT_CSR=./output/cert.csr
CERT_CRT=./output/cert.crt

## Create Private Key for Keycloak route certificate
openssl genrsa -out ${CERT_KEY} 2048
## Create CSR 
openssl req -new -key ${CERT_KEY} -out ${CERT_CSR} \
  -subj "/C=ES/ST=Caribe/L=Macondo/O=ACME/OU=CSA/CN=Keycloak Demo certificate"

## Get the TLS certificate from HAProxy router
echo "*** Get the TLS certificate from HAProxy router"
TMP_TLS_CERT_YAML=./output/cluster-cert.yaml
TMP_TLS_CERT_CRT=./output/cluster-cert.crt
oc get -oyaml \
  -n openshift-ingress \
  $(oc get secret -n openshift-ingress -oNAME | grep "\-ingress") \
  | yq - \
  | yq eval '.data."tls.crt"' \
  | base64 -d > $TMP_TLS_CERT_CRT
## Get the wildcard address form the general cert
echo "*** Get the wildcard address form the general cert"
WILDCARD_ADDRESS=$(openssl x509 -in $TMP_TLS_CERT_CRT -noout -ext subjectAltName \
  | grep DNS \
  | cut -d ':' -f 2 \
  | cut -d ',' -f 1)
rm ${TMP_TLS_CERT_CRT}
export OAUTH_ENDPOINT=oauth-${PROJECT_NAME}${WILDCARD_ADDRESS//\*}
echo "    OAUTH_ENDPOINT=${OAUTH_ENDPOINT}"
## Add Keycloak route to the certificate
CERT_EXT_TEMPLATE=./data/cert.ext
CERT_EXT=./output/cert.ext
cp $CERT_EXT_TEMPLATE $CERT_EXT
echo "DNS.1 = $OAUTH_ENDPOINT" >> $CERT_EXT
## Signing the certificate
openssl x509 -req -in ${CERT_CSR} \
  -CA ${PRIVATE_CA_PEM} -CAkey ${PRIVATE_CA_KEY} -CAcreateserial \
  -out ${CERT_CRT} -days 825 -sha256 -extfile ${CERT_EXT}
## Create TLS secret
TLS_SECRET_NAME=keycloak-route-tls-secret
oc create secret tls $TLS_SECRET_NAME \
  --cert=$CERT_CRT \
  --key=$CERT_KEY
```

### Create keycloak instance

```bash
# --- Create keycloak server --- 
KEYCLOAK_NAME=idp-server
cat <<EOF | oc apply -f -
apiVersion: k8s.keycloak.org/v2alpha1
kind: Keycloak
metadata:
  name: ${KEYCLOAK_NAME}
  labels: 
    observability-demo-framework: idp
spec:  
  ingress: 
    className: openshift-default
    enabled: true
  instances: 2
  hostname: 
    hostname: ${OAUTH_ENDPOINT}
  http: 
    tlsSecret: ${TLS_SECRET_NAME}
  db:
    vendor: postgres
    host: postgres-db
    usernameSecret:
      name: keycloak-database-secret
      key: username
    passwordSecret:
      name: keycloak-database-secret
      key: password
  proxy:
    headers: xforwarded # double check your reverse proxy sets and overwrites the X-Forwarded-* headers
EOF
```

### Import the CSA realm into the created keycloak instance
```bash
oc create -f realm-csa.yaml
```
