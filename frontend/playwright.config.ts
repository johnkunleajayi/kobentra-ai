import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./browser-tests",
  workers: 1,
  use: { baseURL: "http://127.0.0.1:5173", channel: "msedge", headless: true },
  reporter: [
    ["list"],
    ["json", { outputFile: "../work/browser-results.json" }],
  ],
});
