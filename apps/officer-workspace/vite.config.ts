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
    ],
    dedupe: ['react', 'react-dom'],
  },
  server: {
    port: 4000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
