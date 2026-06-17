# Local development with CRC

This guide covers running the React UI and FastAPI control plane on your Mac while using a local CRC cluster for OpenShift resources.

## Prerequisites

- CRC running and logged in (`oc login`)
- `obs-demo` namespace deployed on the cluster (Helm or bash install)
- `podman`, `openssl`, `python3`, `oc`
- Node.js for the frontend

Trust the local development CA once:

```bash
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain \
  obs-main-api/scripts/certs/rootCA.crt
```

## Backend (local API + local Keycloak)

From the repository root:

```bash
obs-main-api/scripts/dev-start.sh --mode local
```

What the script does:

1. Verifies `oc` login and switches to `obs-demo`
2. Generates TLS certs for `localhost` (idempotent)
3. Starts Keycloak in Podman on `https://localhost:8443`
4. Creates a Python venv and launches Uvicorn on `https://localhost:8000`

Useful flags:

- `--mode cluster` — only checks OpenShift context (for frontend-only work against cluster routes)
- `--force-certs` — regenerate certificates

Environment defaults in local mode:

| Variable | Value |
|----------|--------|
| `KEYCLOAK_ISSUER` | `https://localhost:8443/realms/csa` |
| `AGENT_MANAGER` | `mock` |
| `CLUSTER_CONNECTOR` | unset (uses real cluster via kubeconfig) |

## Frontend

### Against local API + local Keycloak

```bash
cd obs-front
npm install
npm run start:local
```

Uses `.env.local`:

```
VITE_OBSERVABILITY_DEMO_API=https://localhost:8000
VITE_KEYCLOAK_URL=https://localhost:8443
```

### Against CRC routes (cluster API + cluster Keycloak)

```bash
cd obs-front
npm run start:crc
```

Update `.env.crc` with your CRC app hostnames if they differ.

## Async operations

Long-running actions return HTTP `202` with an `operationId`. The UI polls `GET /api/v1/operations/{operationId}` and shows live status in the loading overlay.

User sync jobs acquire a Kubernetes `Lease` (`user-sync-lock` in `obs-demo`) to serialize concurrent Keycloak sync operations on the cluster.

In **local mode** (`KEYCLOAK_ISSUER` points to `localhost`), user records are stored in the cluster ConfigMap only. The Ansible sync Job is skipped because the local Podman Keycloak is separate from the cluster IdP.

On **cluster-deployed API**, user sync uses a Kubernetes `Lease` (`user-sync-lock`). If you see `403 Forbidden` on leases, run:

```bash
obs-main-api/scripts/patch-rbac-leases.sh obs-demo
oc rollout restart deployment/obs-main-api -n obs-demo
```

## Troubleshooting

| Issue | Check |
|-------|--------|
| Keycloak login fails | Trust `rootCA.crt`; confirm Podman container `keycloak-local` is running |
| API 401 | `KEYCLOAK_ISSUER` must match Keycloak realm URL |
| User sync hangs | `oc get lease user-sync-lock -n obs-demo`; delete stale lease if needed |
| Simulation create timeout in UI | Ensure API is reachable; check operation status endpoint |
