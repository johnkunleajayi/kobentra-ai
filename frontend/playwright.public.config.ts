import { defineConfig } from "@playwright/test";
import base from "./playwright.config";
export default defineConfig({
  ...base,
  testMatch: "public-motion.spec.ts",
  use: { ...base.use, baseURL: "http://127.0.0.1:5179" },
  webServer: {
    command: "npm run dev -- --port 5179 --strictPort",
    url: "http://127.0.0.1:5179",
    reuseExistingServer: false,
  },
});
