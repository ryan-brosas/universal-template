<!-- capsule-v2 -->
# Block unroll kernel — how do `uses:/with:` references become concrete config blocks without losing order or leaking unresolved inputs?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How do you expand package-referenced blocks in parallel while preserving declaration order and namespacing secrets?

## Parallel unroll with index-preserving reassembly
**Path/Symbol:** `packages/config-yaml/src/load/unroll.ts:unrollAssistantFromContent` (lines 275–333), `unrollBlocks` (367–684), `resolveBlock` (719–766).
**Signature:** `unrollBlocks(assistant: ConfigYaml, registry: Registry, injectBlocks?: PackageIdentifier[], allowlistedBlocks?, blocklistedBlocks?, injectRequestOptions?): Promise<ConfigResult<AssistantUnrolled>>`.
**Data Shape:** sections processed: `["models", "context", "data", "mcpServers", "prompts", "docs"]`; each block result is `{ index, block | null, error | null }`.

### Decisive source
```ts
// parallel per-section AND per-block, but results are written back BY INDEX:
const blockResults = await Promise.all(blockPromises);
for (const result of blockResults) {
  if (result.error) sectionErrors.push(result.error);
  sectionBlocks[result.index] = result.block;   // order survives parallelism
}
// resolveBlock: missing required inputs fail loudly with the block name
const unresolvedInputs = getTemplateVariables(templatedYaml).filter((v) => v.startsWith("inputs."));
if (unresolvedInputs.length > 0) {
  throw new Error(`Missing required input(s) for block "${blockName}": ${missingInputNames.join(", ")}. `
    + `Please provide these values in the "with" block.`);
}
```

**Flow:** parse raw YAML via Zod (`parseConfigYaml`; non-`.yaml/.yml` file ids fall back to markdown-rule parsing — `parseYamlOrMarkdownRule`, 782–809) → for each `uses:` block decode the identifier → allow/block-list check (slug ids only) → `resolveBlock`: fetch content, rewrite `inputs.*` template vars to `secrets.*` FQSNs namespaced by parent slug (`inputsToFQSNs` + `extractFQSNMap`), render `${{ ... }}` vars, throw on unresolved inputs, tag slug-sourced mcpServers with `sourceSlug` → apply shallow `override:` (`mergeOverrides`) → stringify + re-parse whole assistant → optionally render secret values through `platformClient.resolveFQSNs` (user secrets get values; others stay as encoded secret *locations*).
**Invariant:** a failed/unresolvable block becomes a **null slot plus one non-fatal error**, never a reorder; injected local blocks (from `.continue/**`) are appended after declared sections and stamped with `sourceFile` (`injectLocalSourceFile`, 686–717 — bare string rules are wrapped `{ sourceFile, name, rule }`).
**Probe:** `packages/config-yaml/src/load/unroll.test.ts` pins the parse fork ("parses markdown rule content as AssistantUnrolled", "Every non-YAML file is a rule") and `replaceInputsWithSecrets` edge cases including whitespace and malformed variables.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "BlockDuplicationDetector dedup blocks", limit: 8 });
// top hits: BlockDuplicationDetector.constructor/check/isDuplicated/isRuleDuplicated @ packages/config-yaml/src/load/blockDuplicationDetector.ts
await mcp.codebase_memory.trace_path({ project: "continue", function_name: "continue.core.config.yaml.loadYaml.loadConfigYaml", direction: "outbound", depth: 2 });
// shows unrollAssistant -> unrollAssistantFromContent -> unrollBlocks chain across package boundary
```

## Verdict
Adopt index-preserving parallel expansion, inputs→secrets FQSN namespacing, and the loud missing-input error; adapt the registry/FQSN machinery or replace with plain file includes; omit proxy secret locations without a secrets service. Coverage caveat: runner not installed this pass (see work record); probes cite test source read directly.
