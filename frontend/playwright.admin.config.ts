import { defineConfig } from "@playwright/test";
import base from "./playwright.config";
export default defineConfig({
  ...base,
  testMatch: ["admin.spec.ts", "deletion.spec.ts"],
  use: { ...base.use, baseURL: "http://127.0.0.1:5176" },
  webServer: {
    command: "npm run dev -- --port 5176 --strictPort",
    url: "http://127.0.0.1:5176",
    reuseExistingServer: false,
  },
});
