import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
    plugins: [react()],
    root: "client",
    // lucide-react ships some .map files that esbuild treats as JS and can fail to parse (e.g. wifi.js.map).
    // Skipping pre-bundle avoids that; icons load as native ESM in dev.
    optimizeDeps: {
        exclude: ["lucide-react"],
        include: [
            "react",
            "react-dom",
            "react-dom/client",
            "wouter",
            "@tanstack/react-query",
            "date-fns",
            "i18next",
            "react-i18next",
        ],
    },
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "client/src"),
            "@shared": path.resolve(__dirname, "shared"),
        },
    },
    server: {
        host: "0.0.0.0",
        port: 5000,
        allowedHosts: true,
        proxy: {
            "/api": {
                target: "http://127.0.0.1:8000",
                changeOrigin: true,
                secure: false,
            },
        },
    },
    build: {
        outDir: "../dist/public",
        emptyOutDir: true,
        rollupOptions: {
            output: {
                manualChunks: (id) => {
                    if (!id.includes('node_modules')) return undefined;
                    if (id.includes('react-dom') || id.includes('/react/')) return 'react-vendor';
                    if (id.includes('@radix-ui') || id.includes('cmdk')) return 'radix-ui-vendor';
                    if (id.includes('@tanstack')) return 'query-vendor';
                    if (id.includes('date-fns')) return 'date-vendor';
                    if (id.includes('i18next') || id.includes('react-i18next')) return 'i18n-vendor';
                    if (id.includes('lucide-react')) return 'icons-vendor';
                }
            }
        },
        chunkSizeWarningLimit: 1000
    },
});
