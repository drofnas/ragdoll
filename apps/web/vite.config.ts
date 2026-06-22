import { resolve } from "node:path";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react-swc";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@contracts": resolve(__dirname, "../../packages/contracts/typescript")
    }
  },
  server: {
    host: "0.0.0.0",
    port: 3000,
    allowedHosts: ["frontend"],
    fs: {
      allow: [resolve(__dirname), resolve(__dirname, "../../packages/contracts")]
    },
    watch: {
      usePolling: true
    }
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    globals: true,
    css: true,
    restoreMocks: true
  }
});
