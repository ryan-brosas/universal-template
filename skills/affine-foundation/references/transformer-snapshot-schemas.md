<!-- capsule-v2 -->
# Snapshot schemas & Slice envelope — what is the wire contract every snapshot must satisfy?

**Source:** AFFiNE MIT `canary@<pin>`; Codebase Memory `ext-affine`. **Question:** What are the exact zod shapes validated at the transformer boundary, and how do slices carry workspace/page identity?

## Three zod schemas + CRUD interfaces
**Path/Symbol:** `blocksuite/framework/store/src/transformer/type.ts:6-74`; `Slice` class in `transformer/slice.ts:11-39`.
**Signature:** `BlockSnapshotSchema`, `DocSnapshotSchema` (+ private `DocMetaSchema` :50-55), `SliceSnapshotSchema`; `interface BlobCRUD { get; set; delete; list }` (:63-68), `interface DocCRUD { create(id): Store; get(id): Store | null; delete(id) }` (:70-74).
**Data Shape:** `BlockSnapshot = { type:'block', id, flavour, version?, props: Record<string,unknown>, children: BlockSnapshot[] }` — note children is REQUIRED in the type but the schema's `z.lazy(() => BlockSnapshotSchema.array())` (:21) enforces it recursively at validation time.

### Decisive source
```ts
// type.ts:57-61 — doc envelope pins meta shape incl. backward-compat tags
export const DocSnapshotSchema: z.ZodType<DocSnapshot> = z.object({
  type: z.literal('page'),
  meta: DocMetaSchema,          // { id, title, createDate: number, tags: string[] }
  blocks: BlockSnapshotSchema,  // exactly ONE root block node
});
// slice.ts:26-38 — identity comes from the SOURCE doc at construction
static fromModels(doc: Store, models: DraftModel[] | BlockModel[]) {
  ...
  return new Slice({ content: draftModels, workspaceId: doc.workspace.id, pageId: doc.id });
}
```

**Flow:** export builds `{type:'page', meta, blocks}` with `_exportDocMeta` hardcoding `tags: [] "for backward compatibility"` (transformer.ts:486) — tags exist in the schema only so old snapshots still parse. Slices round-trip their workspace/page ids through the snapshot so a pasted slice can later be traced to its origin doc.
**Invariant:** (1) `type` literals (`'block' | 'page' | 'slice'`) are discriminating constants — omitting them fails parse even if all fields match. (2) DocSnapshot holds exactly one root block (the page flavour), not an array. (3) `version?` is optional on blocks but DocMeta requires `createDate: number` — porters serializing dates as strings fail validation at import.
**Probe:** `grep -c '\.parse(' blocksuite/framework/store/src/transformer/transformer.ts` → `6`. And `grep -n 'tags: \[\], // for backward compatibility' …transformer/transformer.ts | cut -d: -f1` → `486`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "BlockSnapshotSchema DocSnapshotSchema SliceSnapshot zod lazy", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt these shapes verbatim as the interchange contract for block-editor snapshots. Adapt field names to your domain but keep required-children recursion and discriminated literals. Omit the backward-compat tags field and legacy exports fail validation on upgrade.
