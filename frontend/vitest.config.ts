<<<<<<< HEAD
import path from "path";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
=======
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";
>>>>>>> auto-claude/006-connect-notifications-page-to-real-websocket-event

export default defineConfig({
  plugins: [react()],
  test: {
<<<<<<< HEAD
    // Use jsdom environment to simulate browser DOM
    environment: "jsdom",

    // Enable global test APIs (describe, it, expect, etc.) without imports
    globals: true,

    // Setup files to run before each test file
    setupFiles: ["./src/test/setup.ts"],

    // Coverage configuration
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html", "lcov"],
      exclude: [
        "node_modules/",
        "src/test/**",
        "**/*.test.ts",
        "**/*.test.tsx",
        "**/*.spec.ts",
        "**/*.spec.tsx",
        "**/routeTree.gen.ts",
        "**/*.config.ts",
        "**/*.config.js",
        "dist/",
      ],
      // Coverage thresholds for critical code paths
      thresholds: {
        lines: 70,
        functions: 70,
        branches: 70,
        statements: 70,
      },
    },

    // Test inclusion patterns
    include: ["src/**/*.{test,spec}.{ts,tsx}"],

    // Exclude patterns
    exclude: [
      "node_modules",
      "dist",
      ".idea",
      ".git",
      ".cache",
    ],
=======
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
>>>>>>> auto-claude/006-connect-notifications-page-to-real-websocket-event
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
