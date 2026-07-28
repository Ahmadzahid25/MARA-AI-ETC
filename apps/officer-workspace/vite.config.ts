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
      { find: '@floating-ui/react', replacement: path.join(localModules, '@floating-ui/react') },
      { find: 'deep-equal', replacement: path.join(localModules, 'deep-equal') },
      { find: 'focus-trap-react', replacement: path.join(localModules, 'focus-trap-react') },
      { find: 'react-select', replacement: path.join(localModules, 'react-select') },
      { find: 'sonner', replacement: path.join(localModules, 'sonner') },
      { find: 'tailwind-scrollbar', replacement: path.join(localModules, 'tailwind-scrollbar') },
      { find: 'react', replacement: path.join(localModules, 'react') },
      { find: 'react-dom', replacement: path.join(localModules, 'react-dom') },
    ],
    dedupe: ['react', 'react-dom'],
  },
  server: {
    host: '0.0.0.0',
    port: 4000,
    strictPort: true,
    allowedHosts: true,
    fs: {
      allow: ['../..'],
    },
    proxy: {
      '/api': {
        target: process.env.VITE_API_GATEWAY_URL || 'http://localhost:8051',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 4000,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: process.env.VITE_API_GATEWAY_URL || 'http://localhost:8051',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
