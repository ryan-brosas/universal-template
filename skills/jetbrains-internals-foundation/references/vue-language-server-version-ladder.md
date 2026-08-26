<!-- capsule-v2 -->
# Bundled language-server version ladder (vue-language-tools) - how do you ship THREE major versions of one LSP side-by-side and let each project pick?

**Source:** PhpStorm installed build PS-262.9437.196 (plugins/vuejs-plugin/vue-language-tools/); Codebase Memory project jetbrains-phpstorm. **Question:** How does a vendor bundle incompatible major versions of a language server and a TS plugin so old and new projects both work from ONE install?

## The versioned directory ladder
**Path/Symbol:** language-server/2.2.10/bin/vue-language-server.js, language-server/3.0.11/, language-server/3.3.5/ (three full bundles, ~170k lines each, each dir carrying its build recipe rolldown.config.ts or build.js); typescript-plugin/{README.md, 3.0.11/, 3.3.5/}; typescript-plugin/README.md:3-8 ('Why the path is like this'), :10-17 (bundle procedure naming VueServices.kt as JVM-side version sync point); language-server/README.md -> WEB-68605.
**Data Shape:** directory-per-version ladders selected at runtime by the PROJECT's toolchain version; selection logic rides JVM-side (not in this indexed plane).

### Decisive source
````
# typescript-plugin/README.md (verbatim)
## Why the path is like this
TypeScript only seems to accept the given plugins if there is a `node_modules` folder in the path to them.
Plugins are passed to TypeScript with the flag `--pluginProbeLocations`, and TypeScript probably treats these folders as it would other projects, resolving plugins in relation to them.
- Adjust version everywhere in `package.json`, `VueServices.kt`
- Build it using `rolldown` inside leaf package folder (inside `node_modules/package/name/...`)
````

**Flow:** three full Volar majors live side-by-side; the JVM service layer picks per project. The TS plugin is additionally version-laddered (3.0.11 + 3.3.5 dirs beside the README) AND physically nested inside a node_modules/package/name path although nothing is installed - because tsc --pluginProbeLocations resolves plugin folders like normal projects and requires that path shape (upstream behavior marked 'To be investigated' in-file). Build discipline: bump version in package.json AND VueServices.kt together, then rolldown-build INSIDE the leaf folder so relative resolution keeps working. README points at WEB-68605 declaring the same pattern spans Vue, Svelte, Astro servers.
**Invariant:** never mutate a shipped major in place; ADD a directory and teach the selector. The fake-node_modules nesting is part of the CONTRACT with tsc's resolver, not an accident of layout.
**Probe:** ls executed this run: language-server contains exactly {2.2.10, 3.0.11, 3.3.5, README.md}; typescript-plugin contains {README.md, 3.0.11, 3.3.5}. Graph inventory matches (9 File nodes incl. rolldown.config.ts x2 + build.js).
**Coverage caveat:** the ~170k-line bundles are minified rollups - treated as opaque payloads; only the ladder structure and README contracts are cited.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.query_graph({ project: "jetbrains-phpstorm", query: "MATCH (f:File) WHERE f.file_path STARTS WITH 'plugins/vuejs-plugin/vue-language-tools' RETURN f.file_path ORDER BY path" });
```

## Verdict
Adopt directory-per-major ladders for any embedded language server ecosystem. Adapt selection signals (project manifest versions) to your host. Omit in-place upgrades - they break the older projects still open in other windows.