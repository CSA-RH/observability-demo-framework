# Roadmap

Living plan for paying down technical debt and growing the Observability Demo Framework.
Phases are ordered by dependency: each one makes the next one safer. Tick items as they land.

> Guiding principle: **do not split the backend into microservices before it has tests and
> clear internal module boundaries.** First a tested, modular monolith; then extract services
> along the seams that prove real (mainly RBAC / privilege boundaries).

---

## Current state (snapshot, Nov 2026)

| Area | Observation |
|---|---|
| Backend `obs-main-api` | `main.py` (~500 lines) mixes 14 endpoints, JWT validation, CORS `*` and wiring. `OpenShiftClusterConnector.py` (~1200 lines) owns users, namespaces, workloads, COO stack, alerts, async operations, ConfigMap persistence, cluster info and the user-sync Job. Mock connectors already exist (good seam for tests). Container runs `uvicorn --reload`. JWKS fetched on every request. |
| Tests | Backend `tests/test_main.py` is empty. Frontend `App.test.js` is a CRA leftover and `npm test` (`vite test`) is not a valid runner. Only the Node client has a real Jest suite. |
| Frontend `obs-front` | React + Vite. API/IdP URLs baked in at build time via build args -> images must be built per cluster. |
| Clients `obs-clients` | Node and .NET are real; Go and Java are stubs. No shared API contract. |
| Install | Promoted path: ArgoCD + Helm (`install/helm`, waves 0-4) and `install/gitops/opentelemetry` (raw manifests). Legacy `install/bash` scripts still present. |
| Docs | README from 2024 (claims no authZ, only Node client). Backlog lived in a local, git-ignored `NOTES.md`. |
| Repo hygiene | `lab/` holds ~19 unrelated experiments. No CI. |

---

## Phase 0 - Hygiene

- [x] Tag pre-cleanup state (`legacy-before-phase-0`) so removed content stays reachable.
- [x] Remove `lab/` experiments (recoverable from the tag).
- [x] Remove legacy `install/bash` scripts and `step-by-step-instructions.md`.
  - [x] Relocate the still-used sync-users job image (`install/bash/sync-users/job-image`) to
        `obs-sync-users/` and update the BuildConfig `contextDir`.
- [x] Images: ImageStreams `lookupPolicy.local: false`; Deployments reference fully-qualified
      image names, configurable via `values.yaml` (`images.*`), defaulting to the internal registry.
- [x] Minimal CI (GitHub Actions): Helm lint/template, backend smoke test, frontend build, Node
      client tests, .NET client build.
  - [x] Fixed on the way: mock mode was broken (`MockClusterConnector` lacked
        `retrieve_hostname_from_service_id`); Node client test imported a wrong path and the
        module bound ports on import.
- [ ] Remove now-redundant per-component `deploy.sh` scripts once the GitOps flow covers dev loops.
- [x] Rewrite README with accurate architecture and links; consolidate the local `NOTES.md` backlog
      into this roadmap. Replace CRA boilerplate in `obs-front/README.md`.
- [ ] Keycloak secrets: the promoted install generates them (`bootstrap-keycloak-idp` in the chart).
      `obs-main-api/scripts/import/realm-definition.json` is only used by local dev
      (`scripts/dev-start.sh`); replace its hardcoded client secrets with placeholders generated at
      dev-start time (low priority, local only).

## Phase 1 - Safety net

- [ ] Characterization tests for all endpoints using FastAPI `TestClient` with
      `CLUSTER_CONNECTOR=mock`, `AGENT_MANAGER=mock` and `get_current_user` overridden.
- [ ] Unit tests for `validators.py`, `utils.py`, `operations/*` (lease lock, operation store).
- [ ] Frontend: replace CRA test with Vitest + React Testing Library; fix `npm test`.
- [ ] Pin backend dependencies (`requirements.txt` has no versions).
- [ ] Coverage reporting in CI.

## Phase 2 - Modular monolith (backend)

- [ ] Split `main.py` into FastAPI routers: `users`, `simulation`, `metrics`, `alerts`,
      `operations`, `cluster-info`.
- [ ] Extract auth into its own module; cache JWKS; restrict CORS to the frontend route.
- [ ] Split `OpenShiftClusterConnector` into domain services:
  - `TenantService` - users, namespaces, Keycloak sync job
  - `SimulationService` - deployments, services, routes, kick
  - `MonitoringService` - COO MonitoringStack, ServiceMonitors, alerts
  - `OperationStore` - async operations persistence
  - `CapabilityService` - cluster info, installed operators/features
- [ ] Settings via `pydantic-settings`; replace `print` with structured logging.
- [ ] Remove `--reload` from the production container command.
- [ ] Define a common client API contract (OpenAPI) for `obs-clients` (discovery, capabilities).

## Phase 3 - Installation experience

- [ ] Single entry point: one ArgoCD app-of-apps.
- [ ] Fold `install/gitops/opentelemetry` raw manifests into the Helm chart (or a sub-chart) behind
      flags: `loki.enabled`, `tempo.enabled`, `otel.enabled`, later `serviceMesh.enabled`.
- [ ] Runtime configuration for the frontend (serve `config.json`/env at container start instead of
      Vite build args) so images become cluster-independent.
- [ ] Build images in CI and publish to Quay; chart defaults switch from in-cluster builds to
      `quay.io/...` (in-cluster BuildConfigs kept as an optional value).
- [ ] Consolidate duplicated wave hooks (e.g. operator-check jobs).
- [ ] Document install / uninstall / upgrade; add an uninstall cleanup job.

## Phase 4 - First extracted microservice: capabilities / gamification

- [ ] New service that detects installed operators/CSVs and options (UWM, COO, Loki, Tempo,
      OTel, Service Mesh, Grafana/Perses) and exposes them as "achievements"/checklist.
- [ ] Establish the template for future services: shared auth library, Helm sub-chart, CI
      pipeline, least-privilege ServiceAccount.
- [ ] Next candidates for extraction, driven by RBAC boundaries: tenant management (high
      privilege) vs. simulation (namespace-scoped).

## Phase 5 - Features

- [ ] **Service Mesh**: per-simulation option to enroll user namespaces and inject sidecars; link
      to Kiali graph.
- [ ] **Multitenancy**: OpenShift IdP <-> Keycloak integration
      ([article](https://access.redhat.com/articles/7062788)); per-tenant naming themes from
      labelled ConfigMaps; namespace separation for loki / otel / tempo / user namespaces.
- [ ] Grafana / Perses dashboards; better LogQL queries for the logs view.
- [ ] Alerting receivers configurable from the UI (AlertmanagerConfig).
- [ ] Exemplars (metrics <-> traces), korrel8r integration.
- [ ] Additional clients: Go, Python, Java.
- [ ] cert-manager for internal certificates: self-signed bootstrap Issuer -> root CA Certificate ->
      ClusterIssuer -> per-route Certificates (replaces the openssl-based generation).

## Documentation (continuous)

Write docs alongside each phase under `docs/`:
`architecture.md`, `installation.md`, `development.md`, `user-guide.md`, one page per client.
