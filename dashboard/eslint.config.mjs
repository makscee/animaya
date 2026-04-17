import tsParser from "@typescript-eslint/parser";

// P-1 fallback (17-01): inlined server-only rule after eslint-plugin-server-only@0.1.1
// failed to load on ESLint 10 (pulls @typescript-eslint/utils@7.x LegacyESLint which
// extends a class removed in ESLint 10). Plugin devDep dropped from package.json.
//
// Rule: files matching **/*.server.ts(x) MUST import "server-only" as a top-level
// statement. Mirrors the behavior of eslint-plugin-server-only@0.1.1 for SEC-04.
const serverOnlyRule = {
  meta: {
    type: "problem",
    docs: {
      description:
        "Require files with .server in their name to import 'server-only'",
    },
    schema: [],
    messages: {
      missing:
        "Files with '.server' in their name must import 'server-only' at the top level.",
    },
  },
  create(context) {
    const filename = context.filename || context.getFilename?.() || "";
    if (!/\.server\.(ts|tsx|js|jsx|mjs|cjs)$/.test(filename)) {
      return {};
    }
    let hasServerOnly = false;
    return {
      ImportDeclaration(node) {
        if (node.source && node.source.value === "server-only") {
          hasServerOnly = true;
        }
      },
      "Program:exit"(node) {
        if (!hasServerOnly) {
          context.report({ node, messageId: "missing" });
        }
      },
    };
  },
};

/** @type {import('eslint').Linter.Config[]} */
const eslintConfig = [
  {
    files: ["**/*.ts", "**/*.tsx"],
    ignores: ["**/*.test.ts", "**/*.test.tsx"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: {
      "server-only": { rules: { "server-only": serverOnlyRule } },
    },
    rules: {
      // SEC-04: Enforce that files with .server in their name import "server-only"
      // Prevents accidental omission of the server-only guard on server modules.
      // Test files are exempted — Bun's test runner neutralizes the server-only
      // sentinel via mock.module preload (see bunfig.toml + test-setup.ts), and
      // tests frequently need to import server modules directly without the
      // runtime poison from the real "server-only" package.
      "server-only/server-only": "error",
    },
  },
];

export default eslintConfig;
