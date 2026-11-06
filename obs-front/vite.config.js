import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

import fs from 'fs'
import path from 'path'

// Definimos las rutas a los certificados locales
const keyPath = path.resolve(__dirname, '../obs-main-api/scripts/certs/keycloak.key')
const certPath = path.resolve(__dirname, '../obs-main-api/scripts/certs/keycloak.crt')

// Verificamos si AMBOS archivos existen en el disco
const hasLocalCerts = fs.existsSync(keyPath) && fs.existsSync(certPath)

// https://vitejs.dev/config/
export default defineConfig({
  base: '/',
  plugins: [react()],
  server: {
    // Si existen los certs, configuramos el objeto https. Si no, pasamos false (HTTP plano)
    https: hasLocalCerts ? {
      key: fs.readFileSync(keyPath),
      cert: fs.readFileSync(certPath),
    } : false,
    
    port: 5173,
    host: '0.0.0.0', // '0.0.0.0' es necesario para que OpenShift pueda enrutar el tráfico internamente
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
    // Fixed values so tests never depend on a developer's local .env files.
    env: {
      VITE_OBSERVABILITY_DEMO_API: 'https://obs-main-api.apps.example.com',
      VITE_KEYCLOAK_URL: 'https://keycloak.apps.example.com',
      VITE_KEYCLOAK_REALM: 'csa',
      VITE_KEYCLOAK_CLIENT_ID: 'webauth',
    },
  },
})