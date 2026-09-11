<!-- capsule-v2 -->
# BaseAdapter template + wrapFakeNote — why does every format adapter share one Transformer and get a synthetic note?

**Source:** AFFiNE MIT `canary@<pin>`; Codebase Memory `ext-affine`. **Question:** What does the abstract adapter own versus its subclass, and why are top-level slices wrapped in an `affine:note`?

## Template-method adapter over job-owned snapshot conversion
**Path/Symbol:** `blocksuite/framework/store/src/adapter/base.ts:70-207` (`BaseAdapter`); `wrapFakeNote` :56-68; ASTWalker :225-324.
**Signature:** `constructor(job: Transformer, readonly provider: ServiceProvider)`; concrete hooks: `fromXSnapshot`/`toXSnapshot` (x ∈ block/doc/slice); inherited wrappers `fromDoc(doc)`, `toSlice(payload, doc, parent?, index?)`, etc.
**Data Shape:** Results carry `assetsIds: string[]` alongside `file: AdapterTarget` so callers know which blobs to persist alongside the file.

### Decisive source
```ts
// base.ts:128-142 — wrapper owns snapshotting + note-wrapping; subclass sees a slice snapshot
async fromSlice(slice: Slice) {
  try {
    const sliceSnapshot = this.job.sliceToSnapshot(slice);
    if (!sliceSnapshot) return;
    wrapFakeNote(sliceSnapshot);
    return await this.fromSliceSnapshot({ snapshot: sliceSnapshot, assets: this.job.assetsManager });
  } catch (error) { console.error('Cannot convert slice to snapshot'); console.error(error); return; }
}
// base.ts:56-68 — id '' marks the synthetic envelope
export function wrapFakeNote(snapshot: SliceSnapshot) {
  if (snapshot.content[0]?.flavour !== 'affine:note') {
    snapshot.content = [
      {
        type: 'block',
        id: '',
        flavour: 'affine:note',
        props: {},
        children: snapshot.content,
      },
    ];
  }
}
```

**Flow:** every direction is two-stage: public wrapper (snapshot via shared `job`, error-capture) → abstract converter (pure format logic, receives AssetsManager). `configs` getter exposes `job.adapterConfigs` to subclasses — title middleware writes there, HTML/Markdown adapters read. The paired `ASTWalker` drives converters generically: `_visit` recurses over object/array members of the SOURCE node guarded by `setONodeTypeGuard`, calling enter/leave callbacks that build TARGET nodes on `ASTWalkerContext` (stack-based parent attach).
**Invariant:** (1) `walk()` ends with `if (this.context.stack.length !== 1) throw new BlockSuiteError(1, 'There are unclosed nodes')` (:311-313) — a converter that forgets `closeNode` fails loudly, not silently. (2) `wrapFakeNote` mutates the snapshot in place and only when the head isn't already a note — double-wrap protection is the flavour check. (3) Subclasses must NOT call each other's snapshots; the job instance is the single conversion authority.
**Probe:** `grep -n 'affine:note' …store/src/adapter/base.ts | cut -d: -f1` → `57` (guard) and `62` (envelope). And `grep -n 'unclosed nodes' …adapter/base.ts | cut -d: -f1` → `312`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "BaseAdapter wrapFakeNote fromSliceSnapshot ASTWalker", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the wrapper/abstract split for multi-format exporters. Adapt the note flavour to your document model's container block. Omit the unclosed-node throw and malformed adapters produce truncated exports with no signal.
