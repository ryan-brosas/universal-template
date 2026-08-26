<!-- capsule-v2 -->
# TypeBox command schemas — how do slash commands get typed, self-documenting arguments without a parser?

**Source:** pi-memory-extension MIT `main@f3b4377f46d75e49a8dda65d0408aab70d669839`; Codebase Memory `pi-memory-extension`. **Question:** A porter must decide how host commands declare and validate their arguments — this repo declares TypeBox schemas that document and shape args, but the handler still casts, so what exactly is the schema trusted for?

## Typed parameter declarations (`registerCommand` + `parameters`)
**Path/Symbol:** `pi-memory.ts:371–377` (`/memory:init` registration) and `pi-memory.ts:533–539` (`/memory:promote` registration).
**Signature:** `pi.registerCommand(name, { description: string, parameters: TObject, handler: (args, ctx) => Promise<void> })` — only these two of the seven commands accept arguments; the other five omit `parameters` entirely.
**Data Shape:** init: `{ scope?: string }` optional with usage text in the schema description. promote: three REQUIRED strings `{ inboxFile, targetDir, targetFile }`, each description doubling as inline usage docs.

### Decisive source
```ts
pi.registerCommand("memory:init", {
  parameters: Type.Object({
    scope: Type.Optional(
      Type.String({ description: "Scope: 'global' or 'workspace' (default: workspace)" }),
    ),
  }),
  description: "Initialize Global or Workspace Memory structure",
  handler: async (args, ctx) => {
    const scope = (args.scope as string) || "workspace";
```
```ts
parameters: Type.Object({
  inboxFile: Type.String({ description: "File name in inbox (e.g. checkpoint-xxx.md)" }),
  targetDir: Type.String({ description: "Target directory: knowledge, user, or workspace (default: workspace)" }),
  targetFile: Type.String({ description: "Target file: decisions.md, lessons.md, etc." }),
}),
```

**Flow:** registerCommand receives a TypeBox object schema → the HOST owns parsing/validation/prompting against it → handler receives `args` → code still applies `(args.scope as string) || "workspace"` rather than trusting the declared type.
**Invariant:** The schema is DOCUMENTATION-FIRST: descriptions are user-facing help text and optionality is declared where it exists, but the handler treats `args` as unvalidated (`as string` cast + `|| default`) instead of consuming inferred static types. Port both halves consciously: if your host validates for real, delete the casts; if it doesn't, keep defensive defaults — but never ship a schema whose types the code pretends are enforced. Note also that argument-consuming commands guard independently: promote re-checks `if (!cache)` at :541–544 before touching state, same not-loaded contract as the read commands.
**Probe:** No upstream test suite exists. Pass-4 evidence: runtime schema introspection was attempted and is BLOCKED standalone — `node -e require.resolve('typebox')` ⇒ MODULE_NOT_FOUND on this host, and package.json declares NO dependencies at all (typebox is host-provided). Deterministic substitutes executed: MCP `search_code pattern "Type.Object"` ⇒ Module hits exactly **372;535**; second GREEN retrieve `search_code "parameters: Type"` ⇒ same pair; direct byte-read of both registration blocks (:360–387, :524–553). Adversarial RED observed: BM25 `"command arguments typed validation schema"` ⇒ total:0 — the seam is INVISIBLE without TypeBox vocabulary, so capsules must carry it.
**Coverage caveat:** `check_index_coverage("package.json")` = `metadata_match` (JSON planes are not symbol-indexed); schema facts pinned by direct reads.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_code({ project: "pi-memory-extension", pattern: "Type.Object", limit: 5 });
```
(Executed pass 4: rank-1 Module `pi-memory.ts` matches `372;535` — both schema sites and no others.)

## Verdict
Adopt schema-carrying command registration with descriptions as the single source of usage help, plus explicit `|| default` handling for optional fields. Adapt to the host's native arg-validation (zod/flag parsers) while keeping the two-tier honesty: declared shape vs actually-trusted shape. Omit nothing for argument-less commands — omitting `parameters` IS the declaration. Coverage caveat: no upstream suite and no local typebox; pinned by executed retrieves + byte-cited source ranges.
