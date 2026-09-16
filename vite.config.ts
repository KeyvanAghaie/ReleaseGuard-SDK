import { defineConfig } from "vite";

export default defineConfig({
  root: "frontend",
  build: { outDir: "../frontend-dist", emptyOutDir: true },
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
