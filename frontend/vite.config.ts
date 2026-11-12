import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", ["VITE_", "VERCEL"]);
  if (
    env.VERCEL === "1" &&
    env.VITE_API_BASE_URL &&
    env.VITE_API_BASE_URL !== "/"
  ) {
    throw new Error("Vercel requires the same-origin API proxy: VITE_API_BASE_URL=/");
  }
  return { plugins: [react(), tailwindcss()] };
});
