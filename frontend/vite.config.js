import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, /api/* is proxied to the FastAPI server so no CORS setup is needed.
// Set VITE_PROXY_TARGET if the backend is not on port 8000.
const target = process.env.VITE_PROXY_TARGET || "http://localhost:8000";
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
