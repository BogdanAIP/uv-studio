import { defineConfig, globalIgnores } from "eslint/config";
import nextCoreVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const legacyCompatibilityFiles = [
  "components/AppShell.tsx",
  "components/HomePage.tsx",
  "components/WorkflowPanel.tsx",
  "components/Sandbox/**/*.tsx",
  "components/pipelines/**/*.tsx",
  "components/stages/**/*.{ts,tsx}",
  "lib/workflowApi.ts",
];

export default defineConfig([
  ...nextCoreVitals,
  ...nextTypescript,
  {
    files: legacyCompatibilityFiles,
    rules: {
      // These files were promoted from the pinned VideoClaw frontend and still
      // carry broad dynamic API types plus pre-compiler React patterns. Keep the
      // findings visible while UV Studio replaces the compatibility surfaces,
      // but do not let a dependency-upgrade slice force risky semantic rewrites.
      "@typescript-eslint/no-explicit-any": "warn",
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/immutability": "warn",
      "react-hooks/refs": "warn",
    },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);
