<!-- capsule-v2 -->
# Per-flavour transformer hook — how do block schemas customize snapshot conversion without touching the core?

**Source:** AFFiNE MIT `canary@<pin>`; Codebase Memory `ext-affine`. **Question:** Where is the extension point that lets a block type add asset handling or prop migration during snapshot round-trips?

## `_getTransformer` fallback ladder
**Path/Symbol:** `blocksuite/framework/store/src/transformer/transformer.ts:515-520` (`_getTransformer`), :504-513 (`_getSchema` throw); contract class `blocksuite/framework/store/src/transformer/base.ts:34-89` (`BaseBlockTransformer`).
**Signature:** `_getTransformer(schema: BlockSchemaType)` → `schema.transformer?.(this._transformerConfigs) ?? new BaseBlockTransformer(this._transformerConfigs)`; hook payloads: `toSnapshot({ model, assets })`, `fromSnapshot({ json, assets, children })`.
**Data Shape:** `json: BlockSnapshotLeaf = Pick<BlockSnapshot, 'id' | 'flavour' | 'props' | 'version'>`; return `SnapshotNode = { id, flavour, version, props }`.

### Decisive source
```ts
// base.ts:62-75 — the default fromSnapshot is SYNCHRONOUS and only revives props
fromSnapshot({ json }: FromSnapshotPayload):
    Promise<SnapshotNode<Props>> | SnapshotNode<Props> {
  const { flavour, id, version, props: _props } = json;
  const props = this._propsFromSnapshot(_props);   // fromJSON per key
  return { id, flavour, version: version ?? -1, props };
}
```

**Flow:** every conversion site (`_blockToSnapshot` :388-393, `_convertSnapshotToDraftModel` :448-458, public `snapshotToModelData` :221-232) resolves flavour → schema via `flavourSchemaMap` (missing ⇒ `BlockSuiteError 'Flavour schema not found for <flavour>'`) → asks the schema for its custom transformer → falls back to `BaseBlockTransformer`. The SAME `_transformerConfigs` Map instance (constructor-created, middleware-writable) is handed to every hook, making it the sanctioned channel for cross-hook settings.
**Invariant:** (1) `version ?? -1` means legacy/unversioned snapshots flow through as −1 — porters must NOT treat −1 as an error; it's the "no version recorded" sentinel. (2) `children` are passed to `fromSnapshot` but IGNORED by the default implementation (tree reassembly is the orchestrator's job) — a custom transformer must not insert children itself. (3) Custom transformers may return sync or async values; the pipeline awaits both.
**Probe:** `grep -n 'schema.transformer?\|new BaseBlockTransformer(this._transformerConfigs)' …transformer.ts | cut -d: -f1` → `517`, `518`. Direct tests: `src/__tests__/transformer.unit.spec.ts:76-138` ('snapshot to model') pins Text revival + plain-prop equality through the default transformer.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "BaseBlockTransformer toSnapshot fromSnapshot props", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the schema-carried-transformer-with-default pattern for extensible import/export pipelines. Adapt the config Map to typed options in strongly-typed codebases. Omit the −1 sentinel and you break every pre-versioning document.
