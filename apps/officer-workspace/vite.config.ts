import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { defineConfig } from 'vite';
import tsconfigPaths from 'vite-tsconfig-paths';

const uiDir = path.resolve(__dirname, '../../packages/openhands-ui');
const localModules = path.resolve(__dirname, 'node_modules');

export default defineConfig({
  plugins: [react(), tailwindcss(), tsconfigPaths()],
  resolve: {
    alias: [
      { find: '@openhands/ui', replacement: path.join(uiDir, 'index.ts') },
      { find: 'tailwind-merge', replacement: path.join(localModules, 'tailwind-merge') },
      { find: 'clsx', replacement: path.join(localModules, 'clsx') },
      { find: 'react-bootstrap-icons', replacement: path.join(localModules, 'react-bootstrap-icons') },
    ],
    dedupe: ['react', 'react-dom'],
  },
  server: {
    port: 4000,
    proxy: {
      // API Gateway runs on port 8051 (services/api_gateway/main.py).
      // Rewrite strips /api prefix: frontend calls /api/healthz → gateway sees /healthz
      '/api': {
        target: 'http://localhost:8051',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
