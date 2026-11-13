# Roadmap

Living plan for paying down technical debt and growing the Observability Demo Framework.
Phases are ordered by dependency: each one makes the next one safer. Tick items as they land.

> Guiding principle: **do not split the backend into microservices before it has tests and
> clear internal module boundaries.** First a tested, modular monolith; then extract services
> along the seams that prove real (mainly RBAC / privilege boundaries).

---

## Status (2026-11-09)

Phases 0 and 1 are done, plus the component rename (PR #67), the RHBK 26.6 Keycloak fix (PR #68)
and the operators/operands GitOps split (PR #69). Validated end to end on a fresh CRC: base
install, operators, MinIO/Loki/Tempo/OTel instances; user creation, COO metrics, traces in
Observe > Traces and logs in Observe > Logs.

**Next steps, in order:**

1. Phase 2: move the monitoring stack choice from users to simulations; explicit `admin`/`user`
   roles in the API; settings that remove the orchestrator's own-namespace assumptions; then split
   `main.py` into routers and the connector into domain services.
2. Phase 3: namespace split (`obs-idp`, then `obs-lab` + `obs-usr-<name>`, then `obs-images`);
   operands-only module charts (`minio`, `loki`, `tempo`, `otel`) with per-platform
   StorageClass overlays; one Application per operator; root app-of-apps.
3. Phase 4: capability detection and admin actions (operators, user workload monitoring, real
   health of LokiStack/TempoStack, which Argo CD cannot see as Degraded); user challenges verified
   by outcome (see "Capabilities and challenges").

## Starting point (pre-Phase 0 snapshot, Nov 2026)

Kept for history; component names are the old ones.

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

**Operators vs. operands.** Operators (Subscriptions) are cluster-wide singletons and a cluster
administrator's concern; a shared cluster (ROSA/ARO) may already have them. They live in their own
Application (`observability-lab-operators`), separate from the operands (MinIO, LokiStack,
TempoStack, OTel collector, UIPlugins). The lab's capability detection then tells the admin
whether each operator is installed and healthy, regardless of who installed it.
Users managing their own LokiStack/TempoStack (multi-tenant operands) is out of scope for now.

### Capabilities and challenges (decided 2026-11-13)

The console shows what the cluster can do and lets the administrator act on it. Installation is
not a one-off install-time choice: the lab detects the current state, whoever set it up.

**Lab-level capabilities (administrator).** Each one has a detected *status* and, where the lab is
allowed to change it, an *action*:

| Capability | Detected from | Admin action |
|---|---|---|
| Loki / Tempo / OTel / COO operators | Subscription + CSV phase | Create that operator's Argo CD Application |
| User workload monitoring (UWM) | `enableUserWorkload` in `openshift-monitoring/cluster-monitoring-config`, `prometheus-user-workload` pods | Enable, only where the lab may own that setting |
| Shared operands (MinIO, LokiStack, TempoStack, lab collector, UIPlugins) | CR status conditions (not Argo CD health) | Create the module Application |

- **One Argo CD Application per operator** (today one Application holds all three), so the admin
  can install Loki without Tempo. The manifests already work on any OpenShift flavour; the
  orchestrator/`obs-capabilities` only creates the Application (RBAC to be designed with the
  restricted `AppProject`).
- **Status comes from the cluster, not from Argo CD.** An operator installed outside the lab shows
  as present ("managed externally") and the console offers no Install button for it.
- **UWM is cluster configuration, not an operator.** `cluster-monitoring-config` is shared: Argo CD
  must not own the whole ConfigMap (it would overwrite other keys), so the enable action patches
  only `enableUserWorkload`. On ROSA/ARO the ConfigMap is SRE-managed and UWM is set through the
  platform: there the console shows the status plus a hint, no action.
- Simulation options unlock from capabilities: `user-workload` simulations need UWM, the logs view
  needs Loki ready, traces need Tempo + OTel ready.

**User-level challenges (gamification).** Users work only in their own namespace, so challenges are
namespace-scoped resources they create themselves (by hand with `oc` or guided from the console):

- an `OpenTelemetryCollector` (deployment or sidecar) forwarding to the lab's TempoStack/LokiStack;
- an `Instrumentation` CR plus annotation for auto-instrumentation of a simulated workload;
- later: ServiceMonitors, PrometheusRules, AlertmanagerConfig receivers.

A challenge is completed by **outcome, not object existence**: "your traces arrive in Tempo",
"your logs show up in Loki", "your alert fired". `obs-capabilities` queries the backends for the
user's tenant/namespace and records the achievement.

Per-user LokiStack/TempoStack stays out of scope: users consume the shared, lab-level operands.

**Argo CD RBAC.** The OpenShift GitOps controller is not cluster-admin. Namespaced workloads need
the namespace label `argocd.argoproj.io/managed-by: openshift-gitops`; operand CRs (and the
cluster-scoped UIPlugin) need an explicit ClusterRole, shipped with the operators Application.

### Platform differences (storage)

**Object storage: MinIO on every platform.** MinIO runs on a PVC of the cluster's default
StorageClass, and Loki/Tempo use it via S3. Good enough for demo purposes, so no Azure Storage
Accounts, ODF ObjectBucketClaims or AWS S3 credentials are needed.

**Block storage:** `LokiStack.spec.storageClassName` is mandatory in the CRD schema (and `""`
means "no class", not "default"), so it must be set explicitly. Helm `lookup` does not work under
Argo CD. Approach:

- Each module chart has a default `values.yaml` plus a one-line overlay per platform with the
  StorageClass name: `values-crc.yaml` (`crc-csi-hostpath-provisioner`), `values-rosa.yaml`
  (`gp3-csi`), `values-aro.yaml` (`managed-csi`), `values-odf.yaml`
  (`ocs-storagecluster-ceph-rbd`).
- The module `Application` lists `valueFiles: [values.yaml, values-<platform>.yaml]`.
- The platform is chosen once at bootstrap (root app value) and published in a ConfigMap that the
  orchestrator reads when it creates module Applications.
- Charts fail rendering with a clear message if `storageClassName` is missing (`required`).

### Namespace layout (decided 2026-11-09)

Split by ownership and privilege, not by technology: everything in a namespace shares lifecycle
and blast radius.

| Namespace | Contents | Why separate |
|---|---|---|
| `obs-lab` | `obs-orchestrator`, `obs-console`, state ConfigMaps/Secret, user-sync Job | The app and its own privileged work |
| `obs-idp` | RHBK operator (OwnNamespace), Keycloak, PostgreSQL | Own lifecycle; replaceable (e.g. OpenShift IdP integration); Keycloak secrets isolated |
| `obs-images` | BuildConfigs and ImageStreams (app, clients, sync image) | Build concern only; optional once images come from Quay |
| `obs-usr-<name>` | One per lab user | Consistent prefix, distinct from system namespaces |
| `obs-minio`, `obs-loki`, `obs-tempo`, `obs-otel` | Logging/tracing modules | Already split |

- The **user-sync Job stays with the app**, not in `obs-idp`: it provisions tenants (namespaces,
  RoleBindings, image-puller bindings, OTel resources) with cluster-wide privileges, besides
  syncing Keycloak users. It belongs to the orchestrator's tenant domain (`TenantService`, first
  candidate for extraction in Phase 4).
- **Cross-namespace config is published, not read:** the IdP bootstrap writes the connection info
  (`idp-data`, Keycloak CA) into `obs-lab`; consumers never read from `obs-idp`.
- **Image pulls:** `system:image-puller` bindings on `obs-images` for `obs-lab` service accounts
  and for each `obs-usr-*` namespace (the sync playbook already creates per-user bindings).
- User namespaces keep being discovered by label (`observability-demo-framework=users`), never by
  name prefix.
- Renaming `obs-demo` -> `obs-lab` and `obs-demo-<name>` -> `obs-usr-<name>` orphans existing
  user namespaces: fresh installs only.

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
      `obs-orchestrator/scripts/import/realm-definition.json` is only used by local dev
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
- [ ] Remove "everything lives in my namespace" assumptions from the orchestrator (prerequisite for
      the namespace split): settings for the IdP connection namespace, image registry/namespace
      (sync image, agent images) and user-namespace prefix (`obs-usr-`). Today: the `obs-demo-`
      prefix in `main.py`, `root_namespace: obs-demo` in the sync playbook, and the sync Job image,
      `idp-data` and Job namespace all derived from the orchestrator's own namespace.
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

- [ ] Namespace split, step 1: move RHBK operator, Keycloak and PostgreSQL to `obs-idp` (the
      namespace already exists in the chart, `idpNamespace`, but is empty). IdP bootstrap
      publishes `idp-data` and the Keycloak CA into the app namespace.
- [ ] Namespace split, step 2: rename `obs-demo` -> `obs-lab` and user namespaces to
      `obs-usr-<name>`, together with the monitoring-type migration (both break existing installs).
      Update the Keycloak group/realm naming (`obs-demo-users`) at the same time.
- [ ] Namespace split, step 3: BuildConfigs/ImageStreams to `obs-images`, tied to Quay publishing
      (in-cluster builds become optional); image-puller bindings for `obs-lab` and `obs-usr-*`.
- [ ] Single entry point: one root Argo CD application for the minimal core (Keycloak, COO,
      orchestrator, console). Bootstrap value `platform: crc | rosa | aro | odf`, published in a
      ConfigMap for the orchestrator.
- [x] Restore a working `observability-lab-otel` on fresh clusters: new
      `observability-lab-operators` Application (Loki, Tempo, OTel Subscriptions + Argo CD RBAC
      for operand CRs); `managed-by` label on operand namespaces; `SkipDryRunOnMissingResource`
      and retry on the operands Application. StorageClass still hardcoded for CRC.
- [ ] Split `install/gitops/opentelemetry` raw manifests into one Helm chart per module
      (`minio`, `loki`, `tempo`, `otel`, later `service-mesh`), operands only. Module
      Applications keep `SkipDryRunOnMissingResource=true` and retry.
- [ ] Split `observability-lab-operators` into one Application per operator (Loki, Tempo, OTel),
      each carrying the Argo CD RBAC for its operand CRs, so the admin installs them independently
      and a cluster that already has an operator skips it.
- [ ] Per-platform overlays `values-<platform>.yaml` (StorageClass name only) in each module
      chart; remove the hardcoded `crc-csi-hostpath-provisioner` from the LokiStack; `required`
      check on `storageClassName`. MinIO stays the only object store on all platforms.
- [ ] Restricted `AppProject` (`obs-lab-modules`): source repo limited to this repository,
      allowed destinations/namespaces and resource kinds whitelisted. Without it, creating
      Applications in `default` is effectively cluster-admin.
- [ ] Orchestrator `ModuleService`: create/delete module Applications (`valueFiles: [values.yaml,
      values-<platform>.yaml]`) and report their Argo CD sync/health status. RBAC limited to
      `applications.argoproj.io` in `openshift-gitops`.
- [ ] Admin panel "Modules" section: install / uninstall / status per module.
- [ ] Move the hardcoded MinIO credentials out of the manifests (generated Secret).
- [ ] ~~Enable user workload monitoring at install time~~: replaced by the UWM capability
      (Phase 4), detected and enabled from the console. Until then, `user-workload` simulations
      show no metrics on a fresh cluster unless UWM is enabled by hand.
- [ ] Runtime configuration for the frontend (serve `config.json`/env at container start instead of
      Vite build args) so images become cluster-independent.
- [ ] Build images in CI and publish to Quay; chart defaults switch from in-cluster builds to
      `quay.io/...` (in-cluster BuildConfigs kept as an optional value).
- [ ] Consolidate duplicated wave hooks (e.g. operator-check jobs).
- [ ] Bootstrap Jobs with `ttlSecondsAfterFinished` (e.g. `bootstrap-keycloak-realm`, 300s) are
      deleted by Kubernetes and recreated by Argo CD selfHeal, so they re-run every ~5 minutes.
      Turn them into Argo CD hooks (`hook: Sync`, `hook-delete-policy: BeforeHookCreation`) or
      drop the TTL.
- [x] RHBK 26.6+: Admin REST API rejects tokens without the `kc-admin-api` scope audience (bare
      401). `bootstrap-keycloak-realm` now attaches the scope to `automation-client`.
  - [ ] Local dev (`dev-start.sh`, `quay.io/keycloak/keycloak:latest` + exported
        `realm-definition.json`) likely has the same issue; verify and add `kc-admin-api` to
        `automation-client` there.
- [ ] Document install / uninstall / upgrade; add an uninstall cleanup job.

## Phase 4 - First extracted microservice: capabilities / gamification

See "Capabilities and challenges" in the target model.

- [ ] `obs-capabilities`: detects installed operators/CSVs and options (UWM, COO, Loki, Tempo,
      OTel, Service Mesh, Grafana/Perses) and the real health of shared operands (CR conditions).
      Reports *who* manages each module (lab-managed Argo CD Application vs. installed outside
      the lab) so the Admin panel does not offer "Install" on something already present.
- [ ] Admin actions: install an operator or module (create its Argo CD Application); enable UWM
      by patching only `enableUserWorkload` (disabled on ROSA/ARO, where the console shows a hint).
- [ ] User challenges verified by outcome (traces in Tempo, logs in Loki, alert fired) for
      namespace-scoped resources the user creates (`OpenTelemetryCollector`, `Instrumentation`,
      ServiceMonitor, PrometheusRule); progress shown as achievements per user.
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
