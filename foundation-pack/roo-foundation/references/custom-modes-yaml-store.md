<!-- capsule-v2 -->
# Custom modes YAML store — how do you merge project + global mode definitions with watchers, queues, and hostile YAML?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How do you read/write custom agent modes from `.roomodes` (project) and the global settings file, keep them merged with correct precedence, and survive invisible characters / concurrent writes?

## TTL cache + write queue; project-over-global slug precedence; char-sanitized YAML
**Path/Symbol:** `src/core/config/CustomModesManager.ts` (class :47-1014; `ROOMODES_FILENAME = ".roomodes"` :19; `cacheTTL = 10_000` :48; `queueWrite`/`processWriteQueue` :65-91; `PROBLEMATIC_CHARS_REGEX` :115-118 + `cleanInvisibleCharacters` :122-143; `parseYamlSafely` :147-181 w/ JSON fallback for .roomodes; `getCustomModes` :356-402; `updateCustomMode` :404-463 source-derived target path).
**Signature:** `getCustomModes(): Promise<ModeConfig[]>`; `updateCustomMode(slug, config): Promise<void>`; constructor takes `onUpdate` callback.
**Data Shape:** `{customModes: ModeConfig[]}` in YAML (settings file) or YAML-with-JSON-fallback (.roomodes); every mode tagged `source: "project" | "global"`.

### Decisive source
```ts
// Merge: project slugs WIN and keep their source tag; global fills the rest
const mergedModes = [
    ...roomodesModes.map((mode) => ({ ...mode, source: "project" as const })),
    ...settingsModes.filter((mode) => !projectModes.has(mode.slug))
        .map((mode) => ({ ...mode, source: "global" as const })),
]
await this.context.globalState.update("customModes", mergedModes)  // mirror for sync consumers
// Writes are serialized through a queue so read-modify-write cycles cannot interleave:
await this.queueWrite(async () => { ...updateModesInFile(targetPath, op)... this.clearCache() })
```
Sanitizer maps NBSP→space, zero-widths→removed, smart quotes→ASCII quotes, unicode dashes→hyphen BEFORE yaml.parse (copy-pasted mode files from docs/chat are full of these); parse failure on .roomodes falls back to JSON parse then surfaces a line-numbered user error; non-.roomodes failures log-and-continue. Watchers fire on create/change/delete of BOTH files; updates re-validate via zod (`modeConfigSchema.safeParse`) before any disk touch; update target file is chosen by the mode's SOURCE tag, and the slug is filtered-then-pushed (upsert semantics) inside the queued transaction.
**Flow:** get → TTL-cache check → load both files (sanitized YAML) → project-first merge by slug → persist mirror to globalState → cache {modes, cachedAt}. update → validate → queue → rewrite target file → clearCache → refreshMergedState (which notifies via onUpdate).
**Invariant:** Project modes can never be shadowed by global ones regardless of insertion order; a corrupt file degrades to empty rather than blocking the other source; writes never interleave because only the queue touches files; cache is invalidated on ANY mutation path (update/delete/watcher).
**Probe:** `src/core/config/__tests__/CustomModesManager.spec.ts` (:97 YAML+JSON dual format, :117 .roomodes precedence, :189 10s memoization, :277/:313 invalidation on delete/update, :579 "queues write operations"); yamlEdgeCases + exportImportSlugChange spec siblings cover sanitizer/slug drift.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "CustomModesManager roomodes mergeCustomModes queueWrite cleanInvisibleCharacters", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt precedence-by-source-tag, the write queue around read-modify-write, TTL caching with explicit invalidation, and pre-parse character sanitation. Adapt file names/schema. The invisible-character table is hard-won — model-authored YAML arrives full of typographic characters that silently break strict parsers.
