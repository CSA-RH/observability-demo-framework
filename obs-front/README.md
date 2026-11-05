# obs-front

React + Vite UI of the Observability Demo Framework. See the [root README](../README.md).

| Command | Purpose |
|---|---|
| `npm start` | Vite dev server |
| `npm run start:local` | Dev server with `.env.local` (local Keycloak/API, see `obs-main-api/scripts/DEVELOPMENT.md`) |
| `npm run build` | Production build into `dist/` |
| `npm test` / `npm run test:watch` | Vitest unit and component tests |

Build-time variables (written to `.env` by the `Dockerfile`): `VITE_OBSERVABILITY_DEMO_API`,
`VITE_KEYCLOAK_URL`, `VITE_KEYCLOAK_REALM`, `VITE_KEYCLOAK_CLIENT_ID`.
