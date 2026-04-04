import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/ts/",
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});
