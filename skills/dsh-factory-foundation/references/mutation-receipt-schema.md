<!-- capsule-v2 -->
# Mutation-receipt schema — how do durable file-mutation receipts stay self-consistent?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** What cross-field invariants must a persisted "what changed" receipt satisfy so downstream consumers can trust it?

## fileMutation/output superRefine lattice
**Path/Symbol:** `packages/protocol/src/schema.ts` (`mutationLineCount`, `fileMutation`, `output` superRefines) (:45–77).
**Signature:** zod schemas; `parseFactoryDocument(input)` applies `factoryDocumentSchema.strict()` — unknown fields REJECTED (obsolete shapes like a top-level `patterns` array fail loudly).
**Data Shape:** receipt `{ commitOrder, path, operation: create|modify|delete, additions, deletions, beforeSha256: sha|null, afterSha256: sha|null, diffs[{path, oldText|null, newText}] }`.

### Decisive source
```ts
const invalidHashes = value.operation === 'create'
    ? value.beforeSha256 !== null || value.afterSha256 === null
    : value.operation === 'modify'
      ? value.beforeSha256 === null || value.afterSha256 === null
      : value.beforeSha256 === null || value.afterSha256 !== null
...
if (value.diffs.some(diff => diff.path !== value.path)) ... 'mutation hunk path disagrees with the mutation path'
if (value.operation === 'create' && value.diffs.some(diff => diff.oldText !== null)) ...
const additions = value.diffs.reduce((total, diff) => total + mutationLineCount(diff.newText), 0)
if (value.additions !== additions || value.deletions !== deletions) ... 'mutation line totals disagree with its hunks'
// output level:
if (value.mutations[index].commitOrder <= value.mutations[index - 1].commitOrder) ... 'strictly increasing commit order'
```

**Flow:** parse-time enforcement: hash nullability must match the operation (create = null→sha, modify = sha→sha, delete = sha→null); every hunk path equals the receipt path; creates carry no removed text and deletes retain no added text; declared add/delete line counts equal the hunk contents (trailing-newline-aware count); receipts inside one output use STRICTLY increasing commitOrder.
**Invariant:** Receipts are self-verifying — a consumer never re-diffs the workspace to trust the ledger, because the schema itself rejects internally contradictory receipts at parse time. Line counting treats a trailing `\n` as a terminator, not an extra line.
**Probe:** `packages/protocol/tests/graph.spec.ts` "accepts valid output mutations and rejects inconsistent durable receipts" (pins throws on short hash `/hunk path/`, miscounted `/line totals/`, duplicated order `/strictly increasing/`). Deterministic from repo root: `grep -c 'strictly increasing commit order' packages/protocol/src/schema.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "FactoryFileMutation", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified via sibling name-pattern queries on this project.)

## Verdict
Adopt the superRefine lattice as-is for any receipt ledger. Adapt field names to host diff format. Omit nothing — this is the porting-critical half of the protocol.
