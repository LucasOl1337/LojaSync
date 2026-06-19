import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backendTarget = process.env.LOJASYNC_BACKEND_URL || process.env.VITE_BACKEND_URL || "http://127.0.0.1:8891";
const apiProxyRoutes = [
  "/actions",
  "/auth",
  "/automation",
  "/brands",
  "/catalog",
  "/health",
  "/products",
  "/settings",
  "/totals",
  "/ws",
];

export default defineConfig({
  base: "/",
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(
      apiProxyRoutes.map((route) => [
        route,
        {
          target: backendTarget,
          changeOrigin: true,
          ws: route === "/ws",
        },
      ]),
    ),
  },
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});
