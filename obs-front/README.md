# obs-front

React + Vite UI of the Observability Demo Framework. See the [root README](../README.md).

| Command | Purpose |
|---|---|
| `npm start` | Vite dev server |
| `npm run start:local` | Dev server with `.env.local` (local Keycloak/API, see `obs-main-api/scripts/DEVELOPMENT.md`) |
| `npm run build` | Production build into `dist/` |

Build-time variables (written to `.env` by the `Dockerfile`): `VITE_OBSERVABILITY_DEMO_API`,
`VITE_KEYCLOAK_URL`, `VITE_KEYCLOAK_REALM`, `VITE_KEYCLOAK_CLIENT_ID`.

> `npm test` is not functional yet (CRA leftover). Vitest setup is tracked in the
> [roadmap](../ROADMAP.md) (Phase 1).
