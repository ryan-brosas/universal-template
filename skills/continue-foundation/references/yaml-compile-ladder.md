<!-- capsule-v2 -->
# YAML compile ladder — how does a porter load assistant YAML without letting one bad block kill the whole config?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How do you compile unrolled assistant YAML into a runtime config such that fatal schema errors interrupt the load but every other failure degrades gracefully?

## Compile ladder with a single fatal gate
**Path/Symbol:** `core/config/yaml/loadYaml.ts:loadConfigYaml` (lines 46–139), `core/config/yaml/loadYaml.ts:nonNullifyConfigYaml` (141–154), `core/config/yaml/loadYaml.ts:loadContinueConfigFromYaml` (385–447).
**Signature:** `loadConfigYaml(options: { overrideConfigYaml?: AssistantUnrolled; ideSettings; ide; packageIdentifier }): Promise<ConfigResult<AssistantUnrolled>>`.
**Data Shape:** returns `{ config?, errors: ConfigValidationError[], configLoadInterrupted, configName? }`; each error carries `fatal: boolean`.

### Decisive source
```ts
// Local .continue blocks are collected WITH pre-read content — fs.readFileSync
// fails for vscode-remote:// URIs in WSL (#6242, #7810)
const localBlocks = await getAllDotContinueDefinitionFiles(ide,
  { includeGlobal: true, includeWorkspace: true, fileExtType: "yaml" }, blockType);
...
if (overrideConfigYaml) {
  config = overrideConfigYaml;
  if (localPackageIdentifiers.length > 0) {
    const unrolledLocal = await unrollLocalYamlBlocks(localPackageIdentifiers, ide, await getRegistryClient());
    ...
    config = mergeUnrolledAssistants(config, unrolledLocal.config); // local blocks win
  }
} else {
  const unrollResult = await unrollAssistant(packageIdentifier, await getRegistryClient(),
    { renderSecrets: true, currentUserSlug: "", platformClient: new LocalPlatformClient(ide),
      injectBlocks: localPackageIdentifiers });
}
if (config) {
  errors.push(...validateConfigYaml(nonNullifyConfigYaml(config)));  // validate AFTER null-stripping
}
if (errors?.some((error) => error.fatal)) {
  return { errors, config: undefined, configLoadInterrupted: true };  // THE only interrupt
}
```

**Flow:** collect local block files (content pre-read) → unroll fork (override+merge vs package+inject) → strip nulls per section → schema-validate → **fatal ⇒ interrupted**, else continue → convert to ContinueConfig → apply org shared-config LAST (`modifyAnyConfigWithSharedConfig`, deliberately not try/caught: "has security implications and failure should be fatal") → default `allowAnonymousTelemetry = true`.
**Invariant:** exactly one fatal gate exists, *after* validation of null-stripped config; all other failures (unrollable block, bad prompt file, failed model construction) append non-fatal errors and loading proceeds.
**Probe:** `core/config/profile/doLoadConfig.vitest.ts:110–158` pins the entry fork — a `packageIdentifier` carrying pre-read `content` routes to the YAML loader even when the file is absent from disk; without content it falls back to JSON.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "continue", function_name: "continue.core.config.yaml.loadYaml.loadConfigYaml", direction: "outbound", depth: 2, mode: "calls" });
// observed callees: unrollLocalYamlBlocks, nonNullifyConfigYaml, mergeUnrolledAssistants,
// unrollAssistant, unrollAssistantFromContent, validateConfigYaml, BlockDuplicationDetector
```

## Verdict
Adopt the single-fatal-gate ladder and the pre-read-content trick for remote FS; adapt the block-collection paths and shared-config timing to your host; omit the hub RegistryClient/secret-rendering plumbing if you have no package registry. Coverage caveat: `doLoadConfig.vitest.ts` is parse-partial at line 81 (mock-hoisting comment); the cited test bodies were read directly from source and are intact.
