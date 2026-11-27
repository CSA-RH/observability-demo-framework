# Roadmap

Plan for paying down technical debt and growing the Observability Lab. Phases are ordered by
dependency. Completed work is summarised at the end; details live in the linked PRs.

> Guiding principle: **no microservices before tests and clear module boundaries.** First a tested,
> modular monolith; then extract services along real seams (mainly RBAC / privilege boundaries).

## Status (2026-11-27)

Phases 0 and 1 are done. Phase 2 is done except the monitoring-type move and the API contract: the
backend is a tested modular monolith (routers, auth, roles, settings, domain services; 85%
coverage). Dependencies are current and Dependabot keeps them so. Last full validation on a fresh
CRC: 2026-11-09 (install, user creation, COO metrics, traces, logs).

**Next, in order:**

1. **Breaking release** (fresh installs only): monitoring type moves from users to simulations,
   together with namespace split step 2 (`obs-lab`, `obs-usr-<name>`).
2. **Phase 3** modular install, then **Phase 4** capabilities and challenges.

---

## Target model (decided Nov 2026)

### Roles

| Role | Can do |
|---|---|
| **Administrator** | Create/delete users, install optional modules (Loki, Tempo, OTel, Service Mesh), set lab-wide profiles. Acts as any user by picking them in the user drop-down. |
| **User** | Runs simulations, metrics, alerts and logs in their own namespace. Never installs cluster components. |

Users no longer pick a monitoring stack (`user-workload` / `coo`) when created: each simulation
chooses it.

### Installation

1. **Bootstrap (GitOps):** one root Argo CD Application installs the core: Keycloak, COO,
   `obs-orchestrator`, `obs-console`. The platform (`crc | rosa | aro | odf`) is chosen here and
   published in a ConfigMap.
2. **The administrator** creates users and installs modules from the Admin panel. Each module is an
   Argo CD `Application` created by the orchestrator in a restricted `AppProject`; Argo CD installs,
   the orchestrator never installs operators or operands itself.
3. **Users** play in their namespace.

**Operators vs operands.** Operators are cluster-wide singletons a shared cluster may already have;
they live in their own Applications, one per operator, separate from the operands (MinIO, LokiStack,
TempoStack, collector, UIPlugins). The Argo CD controller is not cluster-admin: namespaces need the
`argocd.argoproj.io/managed-by` label and operand CRs an explicit ClusterRole.

### Capabilities and challenges

The lab detects what the cluster offers, whoever installed it, and lets the admin act on it.

| Capability | Detected from | Admin action |
|---|---|---|
| Loki / Tempo / OTel / COO operators | Subscription + CSV phase | Create that operator's Application |
| User workload monitoring (UWM) | `enableUserWorkload` in `openshift-monitoring/cluster-monitoring-config` | Patch only that key (never own the ConfigMap) |
| Shared operands | CR status conditions, not Argo CD health | Create the module Application |

- Something installed outside the lab shows as "managed externally", with no Install button.
- UWM may be enabled by the lab on self-managed OCP/CRC, ARO and ROSA HCP. On ROSA Classic/OSD the
  ConfigMap is SRE-managed: show status plus an OpenShift Cluster Manager hint, no action.
- Simulation options unlock from capabilities (`user-workload` needs UWM, logs need Loki, traces
  need Tempo + OTel).
- **User challenges** are namespace-scoped resources users create (`OpenTelemetryCollector`,
  `Instrumentation`, later ServiceMonitor, PrometheusRule, AlertmanagerConfig), completed by
  **outcome**, not object existence: traces arrive in Tempo, logs in Loki, the alert fires.
  Per-user LokiStack/TempoStack is out of scope.

### Storage

- **Object storage:** MinIO on a PVC of the default StorageClass, on every platform.
- **Block storage:** `LokiStack.spec.storageClassName` is mandatory (`""` means no class) and Helm
  `lookup` does not work under Argo CD, so each module chart gets a one-line overlay per platform:
  `values-crc.yaml` (`crc-csi-hostpath-provisioner`), `values-rosa.yaml` (`gp3-csi`),
  `values-aro.yaml` (`managed-csi`), `values-odf.yaml` (`ocs-storagecluster-ceph-rbd`), with a
  `required` check.

### Namespaces

Split by ownership and privilege, not technology.

| Namespace | Contents |
|---|---|
| `obs-lab` | Orchestrator, console, state ConfigMaps/Secret, user-sync Job (it provisions tenants with cluster-wide privileges, so it stays with the app) |
| `obs-idp` | RHBK operator, Keycloak, PostgreSQL; publishes `idp-data` and the CA into `obs-lab` (consumers never read from `obs-idp`) |
| `obs-images` | BuildConfigs/ImageStreams; optional once images come from Quay |
| `obs-usr-<name>` | One per user, discovered by label (`observability-demo-framework=users`), never by prefix |
| `obs-minio`, `obs-loki`, `obs-tempo`, `obs-otel` | Modules (already split) |

Renaming `obs-demo` / `obs-demo-<name>` orphans existing user namespaces: fresh installs only.

---

## Open work

### Phase 0-1 leftovers

- [ ] Local dev realm export (`obs-orchestrator/scripts/import/realm-definition.json`) has hardcoded
      client secrets; generate them in `dev-start.sh` (local only, low priority).
- [ ] Tests: `OpenShiftAgentManager` (16%, needs an HTTP fake); console components `LayoutCanvas`,
      `AgentInfo`, `AdminPage` (need Keycloak/Cytoscape fakes).

### Phase 2 - Modular monolith

- [ ] **Monitoring type per simulation** instead of per user (`AdminPage.jsx`, `ApiHelper.js`,
      `AgentInfo.jsx`, `AlertManagement.jsx`, `SimulationPage.jsx`, `operation_tasks.py`, the
      `observability-stack` namespace label). Ships with namespace split step 2.
- [ ] **API contract:** response models in the OpenAPI spec and a common contract for `obs-clients`
      (discovery, capabilities). Align the agent payload (`dns` on OpenShift, `ip` in the mock).

### Phase 3 - Installation experience

- [ ] Namespace split step 1: Keycloak stack to `obs-idp`.
- [ ] Namespace split step 2: `obs-lab` and `obs-usr-<name>`, Keycloak group `obs-demo-users`
      renamed (with the monitoring-type move).
- [ ] Namespace split step 3: builds to `obs-images`, with Quay publishing.
- [ ] One Helm chart per module (`minio`, `loki`, `tempo`, `otel`, later `service-mesh`), operands
      only, with per-platform StorageClass overlays; replaces `install/gitops/opentelemetry`.
- [ ] One Argo CD Application per operator, each with the RBAC for its operand CRs.
- [ ] Root app-of-apps for the core, with the `platform` value.
- [ ] Restricted `AppProject` (`obs-lab-modules`): this repo only, whitelisted destinations and kinds.
- [ ] Orchestrator `ModuleService` (create/delete module Applications, report status) and an Admin
      panel "Modules" section.
- [ ] Generated MinIO credentials instead of hardcoded ones.
- [ ] Console runtime configuration (`config.json` at container start instead of Vite build args),
      so images are cluster-independent.
- [ ] Images built in CI and published to Quay; in-cluster BuildConfigs become optional (and the
      `bootstrap-build-*` Jobs, deliberately not Sync hooks, go away).
- [ ] Consolidate duplicated wave hooks (operator-check Jobs).
- [ ] Document install / uninstall / upgrade; uninstall cleanup Job.

### Maintenance

- [ ] Dismiss the `deepmerge` Dependabot alert (Jest config merging, dev-only, no patched release).
- [ ] Console image: `npm ci` instead of `npm install`; pin `ubi9/nginx-124` so Dependabot tracks it.

### Phase 4 - Capabilities and gamification (first extracted service)

- [ ] `obs-capabilities`: operator/CSV and UWM detection, real operand health, who manages each module.
- [ ] Admin actions: install an operator/module, enable UWM where allowed (needs `platform` to tell
      ROSA Classic from HCP).
- [ ] User challenges verified by outcome; achievements per user.
- [ ] Simulation options enabled by detected capabilities.
- [ ] Template for future services: shared auth library, Helm sub-chart, CI, least-privilege SA.
- [ ] Next extraction candidates by RBAC boundary: tenant management vs simulation.

### Phase 5 - Features

- [ ] Service Mesh: per-simulation sidecar injection, Kiali link.
- [ ] Multitenancy: OpenShift IdP <-> Keycloak ([article](https://access.redhat.com/articles/7062788));
      admin-managed profiles (pod naming themes, dashboards).
- [ ] Grafana / Perses dashboards; better LogQL for the logs view.
- [ ] Alerting receivers from the UI (AlertmanagerConfig).
- [ ] Exemplars (metrics <-> traces), korrel8r.
- [ ] More clients: Go, Python, Java (Go and Java are stubs).
- [ ] cert-manager for internal certificates (replaces the openssl-based generation).

---

## Done

**Phase 0 - Hygiene.** Pre-cleanup state tagged `legacy-before-phase-0`; `lab/` experiments and
legacy `install/bash` removed; image references parametrised (`images.*`); CI (Helm, backend,
console, Node and .NET clients); README rewritten. Per-component `deploy.sh` scripts removed: the
chart's BuildConfigs build local commits with `oc start-build --from-repo` (README, "Upgrading
images on a cluster").

**Phase 1 - Safety net.** API characterisation and auth tests against mock backends, unit tests,
Vitest for the console, pinned dependencies, coverage ratchet in CI (now 80%). The known gaps
recorded as expected-failure tests are all fixed (409/404/422, JWKS cache, reserved usernames in the
UI validator).

**Phase 2 - Modular monolith** (PRs #67, #73, #75-#79, #100).
- Components renamed: `obs-main-api` -> `obs-orchestrator`, `obs-front` -> `obs-console`.
- `main.py` split into routers; request models (422s with the `{"message": ...}` shape).
- Auth module: PyJWT (RS256 only, `exp`/`iss`/`aud` required), JWKS cache with rotation handling;
  CORS limited to the console.
- `pydantic-settings`; namespaces and images from `NamespaceLayout` (`APP_NAMESPACE`,
  `USER_NAMESPACE_PREFIX`, `IMAGE_REGISTRY`, `IMAGE_NAMESPACE`); JSON structured logging; no
  `--reload` in the image.
- `OpenShiftClusterConnector` split into `TenantService`, `SimulationService`, `MonitoringService`,
  `CapabilityService`, `OperationStore` (`app/services`), tested against an in-memory Kubernetes
  API (`tests/fake_kube.py`).
- Roles: administrators have the `obs-admin` realm role (`ADMIN_ROLE`, read from
  `realm_access.roles`); every other authenticated user is a user, with no role needed. User
  management is admin-only, `/users/{user_id}/...` is that user or an admin (403), operations are
  visible to their owner or an admin (404), and admin views no longer depend on the username.

**Phase 3 so far** (PRs #68, #69, #72, #80).
- `observability-lab-operators` Application (Subscriptions + Argo CD RBAC) makes the OTel stack
  work on fresh clusters.
- Bootstrap Jobs are Argo CD Sync hooks; `bootstrap-keycloak-idp` keeps a valid CA and re-applies
  `keycloak-route-ca-secret`.
- RHBK 26.6+: `kc-admin-api` scope attached to `automation-client`.
- Image triggers: a finished in-cluster build rolls out the orchestrator, the console and every
  user's agents (Argo CD ignores the triggered image field).

**Security and dependencies (Nov 2026)** (PRs #86-#89, #101, #102).
- `python-jose` -> PyJWT; Node client `axios` fixed, lockfile committed, CI audits runtime deps.
- Node 24 LTS with pinned UBI images; React 19.
- Unused packages removed (.NET OpenAPI/Swagger, Node OTel logs, `web-vitals`).
- `.github/dependabot.yml` for every ecosystem, with grouped minor/patch updates and a `react` group.
