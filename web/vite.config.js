import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies API calls to the Node backend on :8750 so `npm run dev`
// works standalone. In production the backend serves web/dist directly.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8750",
      "/health": "http://127.0.0.1:8750",
      "/v1": "http://127.0.0.1:8750",
    },
  },
});
