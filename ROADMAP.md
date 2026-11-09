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

## Target model (decided Nov 2026)

### Roles

| Role | Can do |
|---|---|
| **Administrator** | Create/delete users. Install optional modules (Loki, Tempo, OTel, Service Mesh). Set lab-wide profiles (pod naming themes, dashboards, ...). Act as any user by picking them in the user drop-down. |
| **User** | Run simulations, metrics, alerts and logs inside their own namespace. Never installs cluster components. |

Users no longer pick a monitoring stack (`user-workload` / `coo`) when they are created. The choice
moves to each **simulation**, so one user can run different kinds of simulations.

### Installation story

1. **Bootstrap (GitOps):** a single root Argo CD application installs the minimal core:
   Keycloak, COO, `obs-orchestrator`, `obs-console`.
2. **The administrator logs in**, creates users and installs the remaining modules from the Admin
   panel. Each module is an Argo CD `Application` created by the orchestrator in a restricted
   `AppProject`. Argo CD does the installation; the orchestrator never installs operators or
   operands itself.
3. **Users** play with simulations in their namespace. The administrator can do the same for any
   user by selecting them.

### Platform differences (storage)

`LokiStack.spec.storageClassName` is mandatory in the CRD schema (and `""` means "no class", not
"default"), so it must be set explicitly. Helm `lookup` does not work under Argo CD. Approach:

- Each module chart has a default `values.yaml` plus one overlay per platform:
  `values-crc.yaml`, `values-rosa.yaml`, `values-aro.yaml`, `values-odf.yaml` (block StorageClass
  and object-store backend: MinIO, S3, Azure Blob, ODF ObjectBucketClaim).
- The module `Application` lists `valueFiles: [values.yaml, values-<platform>.yaml]`.
- The platform is chosen once at bootstrap (root app value) and published in a ConfigMap that the
  orchestrator reads when it creates module Applications.
- Charts fail rendering with a clear message if `storageClassName` is missing (`required`).

### Component names

| Old | New |
|---|---|
| `obs-main-api` | `obs-orchestrator` |
| `obs-front` | `obs-console` |
| (Phase 4) | `obs-capabilities` |

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

- [x] Characterization tests for all 14 endpoints using FastAPI `TestClient` with mock connectors
      and `get_current_user` overridden (`obs-main-api/tests/api`). Async operations are polled to
      completion; mock storage is isolated per test.
- [x] Auth tests: real JWT validation path with a throwaway RSA key (expired, wrong audience/issuer,
      missing/unknown `kid`, bad signature, Keycloak unreachable).
- [x] Unit tests for `validators.py`, `utils.py`, `operations/*` (operation store, async tasks with
      rollback, lease lock) and alert-rule helpers (`obs-main-api/tests/unit`).
- [x] Fixed on the way: `MockClusterConnector` signatures had drifted from the interface
      (`create_simulation_resources`, `save_alert_definition`, `delete_alert`,
      `delete_alert_definition`), breaking simulation and alerts in mock mode.
- [x] Frontend: Vitest + React Testing Library (`ApiHelper`, `pollOperation`, `ConfirmationModal`,
      `PasswordCell`); `npm test` works. Upgraded `@vitejs/plugin-react` 1.x -> 6.x (required by Vite 8).
- [x] Pin backend runtime and dev dependencies.
- [x] Coverage reporting in CI with a ratchet (`--cov-fail-under`, currently 50%).

Known gaps recorded as strict `xfail` / `it.fails` tests. Fixing one makes its test fail, which
is the signal to turn it into a regular test:

- [ ] Duplicate usernames accepted (expected 409).
- [ ] Deleting an unknown user succeeds (expected 404).
- [ ] Missing payload fields return 500 instead of 422 (no request models).
- [ ] JWKS fetched from Keycloak on every request (no cache).
- [ ] UI username validation does not reject reserved names (`admin`, `cluster-admin`).

Still open:

- [ ] `OpenShiftClusterConnector` / `OpenShiftAgentManager` coverage is 10-15%; add tests with a
      fake Kubernetes client as part of the Phase 2 split.
- [ ] Component tests for `LayoutCanvas`, `AgentInfo`, `AdminPage` (need Keycloak/Cytoscape fakes).

## Phase 2 - Modular monolith (backend)

- [x] **Rename components first** (one dedicated commit, CI as safety net): `obs-main-api` ->
      `obs-orchestrator`, `obs-front` -> `obs-console`. Covers folders, ImageStreams,
      BuildConfigs, Deployments, Services/Routes, RBAC, `values.yaml` `images.*`, CI workflow,
      README, dev scripts. Keycloak clients use wildcard redirect URIs, so only `backend-url`
      (derived from the API Route name) changed.
  - Existing installs: delete Job `bootstrap-keycloak-idp` before syncing (its pod template is
    immutable and now carries the new API host), then rebuild the console image (API URL is
    baked in at build time). Fresh installs need nothing.
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
- [ ] Pydantic request/response models for every endpoint (fixes the 500-vs-422 gap).
- [ ] Move the monitoring stack choice (`user-workload` / `coo`) from user creation to
      simulation creation. Today `monitoringType` lives on the user (`AdminPage.jsx`,
      `operation_tasks.py`, `ApiHelper.js`, `AgentInfo.jsx`, `AlertManagement.jsx`,
      `SimulationPage.jsx`). Includes migrating existing users stored in the ConfigMap.
- [ ] Explicit roles: `admin` vs `user` Keycloak realm roles enforced in the API (admin-only:
      user management, modules, profiles). Admin can target any user's namespace; users only
      their own.
- [ ] Remove `--reload` from the production container command.
- [ ] Define a common client API contract (OpenAPI) for `obs-clients` (discovery, capabilities).

## Phase 3 - Installation experience

See "Target model" above for the decided installation story.

- [ ] Single entry point: one root Argo CD application for the minimal core (Keycloak, COO,
      orchestrator, console). Bootstrap value `platform: crc | rosa | aro | odf`, published in a
      ConfigMap for the orchestrator.
- [ ] Split `install/gitops/opentelemetry` raw manifests into one Helm chart per module
      (`minio`, `loki`, `tempo`, `otel`, later `service-mesh`). Each chart bundles the operator
      Subscription and its operand (e.g. LokiStack) with sync waves, so one module = one
      Application (operand CRs need `SkipDryRunOnMissingResource=true`).
- [ ] Per-platform overlays `values-<platform>.yaml` in each module chart; remove the hardcoded
      `crc-csi-hostpath-provisioner` from the LokiStack; `required` check on `storageClassName`.
- [ ] Restricted `AppProject` (`obs-lab-modules`): source repo limited to this repository,
      allowed destinations/namespaces and resource kinds whitelisted. Without it, creating
      Applications in `default` is effectively cluster-admin.
- [ ] Orchestrator `ModuleService`: create/delete module Applications (`valueFiles: [values.yaml,
      values-<platform>.yaml]`) and report their Argo CD sync/health status. RBAC limited to
      `applications.argoproj.io` in `openshift-gitops`.
- [ ] Admin panel "Modules" section: install / uninstall / status per module.
- [ ] Move the hardcoded MinIO credentials out of the manifests (generated Secret).
- [ ] Runtime configuration for the frontend (serve `config.json`/env at container start instead of
      Vite build args) so images become cluster-independent.
- [ ] Build images in CI and publish to Quay; chart defaults switch from in-cluster builds to
      `quay.io/...` (in-cluster BuildConfigs kept as an optional value).
- [ ] Consolidate duplicated wave hooks (e.g. operator-check jobs).
- [ ] Document install / uninstall / upgrade; add an uninstall cleanup job.

## Phase 4 - First extracted microservice: capabilities / gamification

- [ ] `obs-capabilities`: detects installed operators/CSVs and options (UWM, COO, Loki, Tempo,
      OTel, Service Mesh, Grafana/Perses) and exposes them as "achievements"/checklist. Reports
      *who* manages each module (lab-managed Argo CD Application vs. installed outside the lab)
      so the Admin panel does not offer "Install" on something already present.
- [ ] Simulation options in the console are enabled/disabled based on detected capabilities
      (e.g. logs view only when Loki is ready, traces only when Tempo + OTel are ready).
- [ ] Establish the template for future services: shared auth library, Helm sub-chart, CI
      pipeline, least-privilege ServiceAccount.
- [ ] Next candidates for extraction, driven by RBAC boundaries: tenant management (high
      privilege) vs. simulation (namespace-scoped).

## Phase 5 - Features

- [ ] **Service Mesh**: per-simulation option to enroll user namespaces and inject sidecars; link
      to Kiali graph.
- [ ] **Multitenancy**: OpenShift IdP <-> Keycloak integration
      ([article](https://access.redhat.com/articles/7062788)); admin-managed **profiles**
      (pod naming themes from labelled ConfigMaps, dashboards/graphics) assignable per user; namespace separation for loki / otel / tempo / user namespaces.
- [ ] Grafana / Perses dashboards; better LogQL queries for the logs view.
- [ ] Alerting receivers configurable from the UI (AlertmanagerConfig).
- [ ] Exemplars (metrics <-> traces), korrel8r integration.
- [ ] Additional clients: Go, Python, Java.
- [ ] cert-manager for internal certificates: self-signed bootstrap Issuer -> root CA Certificate ->
      ClusterIssuer -> per-route Certificates (replaces the openssl-based generation).

## Documentation (continuous)

Write docs alongside each phase under `docs/`:
`architecture.md`, `installation.md`, `development.md`, `user-guide.md`, one page per client.
