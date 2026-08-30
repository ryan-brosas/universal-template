<!-- capsule-v2 -->
# Vue language-tools bundling matrix — how do you bundle Vue language support that must plug into multiple TypeScript versions at once?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145`; Codebase Memory `jetbrains-webstorm`. **Question:** above.

## Version-pinned server dirs + node_modules-bearing plugin probe paths
**Path/Symbol:** `plugins/vuejs-plugin/vue-language-tools/`: `language-server/{2.2.10,3.3.5}/` (each with bin/, package.json, package-lock.json; 3.3.5 adds rolldown.config.ts), `typescript-plugin/{3.0.11,3.3.5}/node_modules/@vue/typescript-plugin/`, `README.md`; legacy plane `plugins/vuejs-plugin/vue-service/node_modules/ws-typescript-vue-plugin`.
**Signature:** n/a (layout + README contract, not a callable).
**Data Shape:** one directory per shipped language-server version; one directory per @vue/typescript-plugin major, each FORCED through a synthetic `node_modules/@vue/typescript-plugin` nesting.

### Decisive source
\`\`\`markdown
<!-- typescript-plugin/README.md, verbatim — the load-bearing invariant: -->
TypeScript only seems to accept the given plugins if there is a `node_modules` folder in the path to them.
Plugins are passed to TypeScript with the flag `--pluginProbeLocations`, and TypeScript probably treats these folders as it
would other projects, resolving plugins in relation to them.

## How to bundle
- Adjust version everywhere in `package.json`, `VueServices.kt`
- Build it using `rolldown` inside leaf package folder (inside `node_modules/package/name/...`)
\`\`\`

**Flow:** JVM (`VueServices.kt`) picks the matching language-server dir + ts-plugin dir for the project's TS/Volar combination → passes the plugin dir via `--pluginProbeLocations` → TypeScript resolves the plugin RELATIVE to that path, which only works because the path contains a `node_modules` segment → multiple versions coexist so different projects hit different pairs.
**Invariant:** (1) the artificial `node_modules/@vue/typescript-plugin` nesting is NOT packaging noise — removing it breaks TS plugin probing; (2) version bumps are two-surface (package.json + Kotlin constant) and must land together; (3) old tsserver-based support (`ws-typescript-vue-plugin`) ships BESIDE the new Volar servers during the migration window — do not delete either while both code paths exist.
**Probe:** layout verified by direct ls (language-server/{2.2.10,3.3.5}, typescript-plugin/{3.0.11,3.3.5}/node_modules/@vue/typescript-plugin, vue-service/node_modules/ws-typescript-vue-plugin). README coverage: check_index_coverage → no_recorded_issue.

## Get live surrounding code
**Retrieve:**
\`\`\`ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", query: "vue language service typescript plugin", limit: 12 });
// top hits live INSIDE language-server/2.2.10/bin/vue-language-server.js bundled volar-service-typescript rows
// plus javascript-plugin service-loader.getService — the two planes this matrix sits between
\`\`\`

## Verdict
Adopt the probe-path discipline (any TS-hosted plugin must be reachable under a path containing `node_modules`) and the coexisting-version-matrix layout for any language server straddling host-version majors. Adapt version-pair selection policy to your host. Omit rolldown specifics; keep only "build INSIDE the leaf node_modules folder" as the constraint that preserves the invariant.
