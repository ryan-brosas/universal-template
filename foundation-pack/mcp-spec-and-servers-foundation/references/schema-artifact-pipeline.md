<!-- capsule-v2 -->
# Schema artifact pipeline — how is the published schema.json kept byte-honest across protocol versions with different JSON Schema dialects?

**Source:** modelcontextprotocol (specification) MIT `main@57ac4a2ec742e0cb7622d899b0f5d3bcf769fd69`; Codebase Memory `modelcontextprotocol`. **Question:** When my product publishes a versioned wire-schema JSON derived from TypeScript types, how do I prevent hand-edited drift while serving legacy draft-07 and modern 2020-12 dialects from one pipeline?

## Generated-artifact drift gate over an era-partitioned version set
**Path/Symbol:** `scripts/generate-schemas.ts:generateSchema` (52–110) with `applyJsonSchema202012Transformations` (25–47), `LEGACY_SCHEMAS`/`MODERN_SCHEMAS` (11–14), `main` check branch (115–131).
**Signature:** `async function generateSchema(version: string, check: boolean = false): Promise<boolean>`.
**Data Shape:** version ∈ LEGACY `['2024-11-05','2025-03-26','2025-06-18']` (stay draft-07) or MODERN `['2025-11-25','2026-07-28','draft']` (2020-12); input `schema/<v>/schema.ts`, output `schema/<v>/schema.json`; returns per-version validity in check mode; process exits 1 naming the fix command.

### Decisive source
```ts
const CHECK_MODE = process.argv.includes('--check');
// generation (both modes run the same tool):
// npx typescript-json-schema --defaultNumberType integer --required --skipLibCheck "<dir>/schema.ts" "*"
if (!LEGACY_SCHEMAS.includes(version)) {
  expectedSchema = expectedSchema.replace(/http:\/\/json-schema\.org\/draft-07\/schema#/g,
    'https://json-schema.org/draft/2020-12/schema');
  expectedSchema = expectedSchema.replace(/"definitions":/g, '"$defs":');
  expectedSchema = expectedSchema.replace(/#\/definitions\//g, '#/$defs/');
}
if (existingSchema.trim() !== expectedSchema.trim()) {
  console.error(`  ✗ Schema ${version} is out of date!`);
  return false;
}
```

**Flow:** schema.ts (source of truth) → typescript-json-schema regenerates ALL exported types → if modern era, apply the SAME three regex transforms (dialect URL, definitions→$defs, ref prefix) on BOTH write and verify paths → write file, or trim-compare regenerated-vs-committed and exit 1 with `npm run generate:schema:json` when any of the six versions drifts.
**Invariant:** committed `schema.json` bytes always equal regenerated+transformed bytes; the era split lives in ONE data array plus ONE transform applied identically in write and check branches — a hand edit (e.g. renaming `$defs`→`definitions`) MUST fail CI.
**Probe:** `npm run check:schema:json` at HEAD ⇒ "All schemas are up to date!", exit 0. RED twin: replace `$defs`→`definitions` in `schema/draft/schema.json` (279 occurrences) ⇒ "✗ Schema draft is out of date!" + "Error: Some schemas are out of date." + exit 1 (observed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", query: "generateSchema", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt generated-artifact discipline (derive published JSON from typed sources; gate CI on regenerate-and-compare equality with the fix command in the error) and the data-driven era partition with a single shared dialect transform. Adapt generator choice (typescript-json-schema) and transform regexes to your schema toolchain. Omit the specific MCP version list and Hugo/docs-site coupling. Coverage: scripts/generate-schemas.ts indexed no_recorded_issue/metadata_match (FULL graph, best-effort caveat); no unit test file exists for this script — the repo's own npm gate IS the probe.
