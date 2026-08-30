<!-- capsule-v2 -->
# Prettier config resolve subprocess — how do you read a project's prettier config using THEIR prettier version without depending on prettier?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145`; Codebase Memory `jetbrains-webstorm`. **Question:** above.

## Two-argv subprocess contract over the user's own module
**Path/Symbol:** `plugins/prettierJS/prettierLanguageService/convert-prettier-config.js`: top-level argv reads (:39-41), `main()` (:42-55). This file is the graph's single declared entry point for the whole install.
**Signature:** CLI: `node convert-prettier-config.js <modulePath> <configFilePath>` → JSON config object on stdout.
**Data Shape:** argv[2] = resolvable path of the USER's prettier module; argv[3] = the config file path to resolve. Output: `JSON.stringify(config)` or empty output when resolveConfig yields null (no config found).

### Decisive source
\`\`\`js
var modulePath = process.argv[2];
var configFilePath = process.argv[3];
var prettier = require(modulePath);                       // THE USER'S copy, by path
…
case 0: return [4 /*yield*/, prettier.resolveConfig(configFilePath, { config: configFilePath, editorconfig: false })];
case 1:
    config = _a.sent();
    console.log(JSON.stringify(config));
\`\`\`

**Flow:** JVM linter service spawns node with the user's prettier location → subprocess requires THAT module → `resolveConfig` pinned to exactly the given file with editorconfig cascading disabled → result serialized as one JSON line for the parent to parse.
**Invariant:** config semantics MUST come from the user's installed prettier (require by path), never a bundled copy — otherwise option defaults drift per user version; `editorconfig:false` keeps .editorconfig from silently overriding prettier files during conversion; the config search anchor is the file itself (`config: configFilePath`), so resolution cannot wander up past the intended root.
**Probe:** `node --check convert-prettier-config.js` → OK (executed). Live end-to-end run requires a project-local prettier install (caveat recorded). Coverage: check_index_coverage → no_recorded_issue.

## Get live surrounding code
**Retrieve:**
\`\`\`ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "prettier config convert", limit: 6 });
// rank set: convert-prettier-config.{main,step,verb,…} all @ convert-prettier-config.js
\`\`\`

## Verdict
Adopt the subprocess-with-user-module pattern for ANY tool whose config grammar you must mirror (prettier/eslint/biome): the tool's own resolver is the only spec-compliant parser. Adapt argv plumbing to your IPC preference (stdout JSON line here). Omit the compiled TS helper prelude (__awaiter/__generator) — build your own from scratch.
