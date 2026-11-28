import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" + HashRouter = works on any GitHub Pages path without server config
export default defineConfig({ plugins: [react()], base: "./" });
