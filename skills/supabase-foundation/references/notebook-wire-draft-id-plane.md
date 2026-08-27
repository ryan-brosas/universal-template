<!-- capsule-v2 -->
# Notebook wire/draft-id plane — how does a document keep cell identity honest across client drafts, agent writes, and backend-assigned ids?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** What schema-layer machinery lets a cell exist client-side BEFORE the backend assigns it an id, keeps agent-supplied ids out of the system entirely, and makes a new cell type impossible to add without classifying it?

## Draft-id lifecycle + wireId strip (`data/content/notebooks/notebook-schema.ts`)
**Path/Symbol:** `apps/studio/data/content/notebooks/notebook-schema.ts` : `DRAFT_ID_PREFIX` (:179), `generateDraftId` (:181-183), `isDraftId` (:185-187), `wireId` (:189-191), `toWireWritableCell` (:237-252).
**Signature:** `generateDraftId(): string`; `wireId(id?: string): { _id: string } | Record<string, never>` (private).
**Data Shape:** three identity states for a cell: (1) no id at all (brand-new, never saved); (2) a DRAFT id (`draft-<uuid>`, minted client-side for React keys/state lookups before the first save); (3) a real backend-assigned `_id` (the backend assigns one on every write and returns it on every read). `wireId` collapses states 1 and 2 to NO `_id` on the wire — a draft-id cell reaches the backend exactly like a brand-new one, so the backend never sees a client-fabricated id.

### Decisive source
```ts
// A draft id fills that gap. It's never sent to the backend as a real `_id`
// (see wireId below): a cell with a draft id reaches the wire exactly like a
// brand-new one, so the backend assigns its own.
const DRAFT_ID_PREFIX = 'draft-'

export function generateDraftId(): string {
  return `${DRAFT_ID_PREFIX}${crypto.randomUUID()}`
}

export function isDraftId(id: string): boolean {
  return id.startsWith(DRAFT_ID_PREFIX)
}

function wireId(id: string | undefined): { _id: string } | Record<string, never> {
  return id !== undefined && !isDraftId(id) ? { _id: id } : {}
}
```

**Flow:** editor mints a draft id on local cell creation → all client state/React keys use it → on save, `toWireWritableCell` spreads the cell and merges `...wireId(_id)` — real ids pass through as `_id`, draft ids and undefined vanish. The backend diffs kept cells against the previous version by their real `_id`; cells arriving without one are created.
**Invariant:** the prefix is the ONLY thing separating "client identity" from "backend identity" — it must be namespaced (never a bare uuid) or a collision with a backend id becomes an undetectable cross-write. The strip happens at ONE boundary (the writable-wire transform), not at every call site.
**Probe:** `notebook-schema.test.ts` (pure vitest, 443L, read whole; unexecutable in-lane — standing block) pins "drops a draft id rather than sending it back as _id", "sends a real id through as _id", and "leaves a cell with no id at all without an _id"; `notebook-upsert-mutation.test.ts` (msw) pins the create body carrying ZERO `_id` properties and the update body keeping the existing `_id` while the new cell has none.

## Writable vs agent vs wire schemas + validation-before-network
**Path/Symbol:** same file : `writableCellSchema` (:124-137), `agentCellSchema` (:157-163); `notebook-upsert-mutation.ts` : `buildNotebookUpsertPayload` (:14-27).
**Signature:** `writableNotebookSchema.parse(content)` runs inside `buildNotebookUpsertPayload` BEFORE the payload object is built.
**Data Shape:** three distinct cell schemas over the same fields: `cellSchema` (wire READ: `_id` REQUIRED — "a cell that's been saved always carries the backend's real `_id`"), `writableCellSchema` (write body: `_id` OPTIONAL — create-shaped = no ids, update-shaped = mix of kept real ids + new no-id cells), `agentCellSchema` (`.strict()`, NO `_id` field at all — comment: "Agents have restrictions on writing IDs to preserve guarantees about ID uniqueness"). Strictness means an agent payload containing any unexpected key (including a smuggled `_id`) fails validation.

### Decisive source
```ts
// Agents have restrictions on writing IDs to preserve guarantees about ID
// uniqueness
export const agentCellSchema = z.discriminatedUnion('_tag', [
  markdownFieldsSchema.extend({ _tag: z.literal('markdown_cell') }).strict(),
  databaseFieldsSchema.extend({ _tag: z.literal('database_cell') }).strict(),
  logFieldsSchema.extend({ _tag: z.literal('log_cell') }).strict(),
])
```

**Flow:** upsert path = `writableNotebookSchema.parse(content)` → build `{ id, name, description, type: 'notebook', visibility: 'project', content }` → PUT via shared content-upsert; malformed content rejects WITHOUT a network request. Agent path = ops validated against `agentCellSchema` (no ids possible) then applied by the operations reducer capsule.
**Invariant:** id authority is layered: backend assigns, client may hold drafts (namespaced), agents may do neither. Each layer is enforced by a SEPARATE schema, not by runtime checks scattered across handlers. Validation-before-network is test-observable: the msw suite asserts the invalid-content call throws with no PUT issued.
**Probe:** `notebook-schema.test.ts` pins "rejects cells that carry an agent-supplied id", "accepts a notebook where every cell lacks an id (create-shaped)", "accepts a notebook with a mix of cells with and without an id (update-shaped)", "rejects a cell with no _id — the backend always assigns one on save" (read-side). `notebook-upsert-mutation.test.ts` pins validation-before-network for both create and upsert.

## Compile-time cell-kind registration + bounds
**Path/Symbol:** same file : `CELL_KINDS` (:271-278), `QueryCellTag` (:279-282), `isQueryCell` (:290-292), `MAX_CHART_Y_SERIES` (:17), `timeRangeSchema` refine (:40-55).
**Signature:** `const CELL_KINDS = { markdown_cell: 'content', database_cell: 'query', log_cell: 'query' } as const satisfies Record<Cell['_tag'], CellKind>`; `isQueryCell<C extends { _tag: Cell['_tag'] }>(cell: C): cell is Extract<C, { _tag: QueryCellTag }>`.
**Data Shape:** the `satisfies Record<Cell['_tag'], CellKind>` clause makes CELL_KINDS the REGISTRATION POINT for a new backend: adding a member to `cellSchema` fails to compile here until it is classified, and `QueryCell`/`isQueryCell` widen automatically once it is — a new cell type can never be silently left out of query-generic UI. `isQueryCell` is generic over its input so it also narrows valtio's deep-readonly `Snapshot<Cell>` values. Bounds: `MAX_CHART_Y_SERIES = 3` caps chart y_series; `timeRangeSchema`'s absolute-range refine requires end > start BUT stays silent when either bound is unparseable (the field-level issue already reports it — a second ordering issue would be misleading).

### Decisive source
```ts
/**
 * Classifies every cell tag as content or query. The `satisfies` clause makes this the
 * registration point for a new backend: adding a member to `cellSchema` fails to compile
 * here until it is classified, and `QueryCell` / `isQueryCell` widen automatically once
 * it is — so a new cell type can never be silently left out of query-generic UI.
 */
const CELL_KINDS = {
  markdown_cell: 'content',
  database_cell: 'query',
  log_cell: 'query',
} as const satisfies Record<Cell['_tag'], CellKind>
```

**Flow:** UI code calls `isQueryCell(cell)` to route cells into query-generic components; the compiler guarantees the classification table stays total over the tag set.
**Invariant:** exhaustiveness-by-construction beats runtime switch audits: the moment a tag exists unclassified, the build breaks at the registration point, not at some consumer that forgot a case. The silent-refine rule generalizes: when two validators can both fire on one bad input, let the FIELD-level one speak and keep the cross-field rule quiet.
**Probe:** `notebook-schema.test.ts` pins "narrows every runnable cell and excludes content cells" (isQueryCell), "rejects an absolute_time_range that does not move forward in time", and "reports an invalid bound against its own field rather than the ordering rule".

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct whole-file reads plus the direct tests at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "DRAFT_ID_PREFIX wireId agentCellSchema writableCellSchema CELL_KINDS isQueryCell", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-schema identity ladder (read-required / write-optional / agent-forbidden ids), the namespaced draft-id prefix stripped at a single wire boundary, strict schemas on every externally-authored surface, validation-before-network in payload builders, and the `satisfies Record<Tag, Kind>` registration point for open/closed type families. Adapt the prefix value and the content-type constants to your domain. Omit nothing structural: the layered id authority is what makes the operations reducer's id-less payloads safe, and the compile-time registration point is cheap insurance against silent UI gaps when the tag set grows.
