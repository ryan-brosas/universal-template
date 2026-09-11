<!-- capsule-v2 -->
# YBlock encoding — sys:*/prop:* keys, flat-data mode, and why the root scan has no parent pointer

**Source:** AFFiNE MIT `canary@b530198a3b5ec1fb9b9eb9b684e428ab9e387d5a`; Codebase Memory project `ext-affine`. **Question:** What exact wire shape does a block occupy inside a Y.Doc, and which structural rules must a porter reproduce byte-for-byte to stay compatible?

## DocCRUD.addBlock + DocCRUD.root
**Path/Symbol:** `blocksuite/framework/store/src/model/store/crud.ts`: `addBlock` (:46-135), `root` getter (:11-23), `isFlatData` branch (:98-117).
**Signature:** `addBlock(id, flavour, initialProps = {}, parent?: string|null, parentIndex?: number)`.
**Data Shape:** every block is a `Y.Map` in top-level `yBlocks` keyed by id with EXACTLY: `sys:id` (string), `sys:flavour` (string), `sys:version` (number), `sys:children` (`Y.Array<string>` of child ids); user props stored as sibling keys `prop:<name>` with values converted via `native2Y` (Text→Y.Text, objects→nested Y.Map, arrays→Y.Array). Flat-data mode instead stores dotted paths `prop:a.b.c` → leaf primitives.

### Decisive source
```ts
// crud.ts :75-86 — creation writes sys keys in fixed order and clamps parentIndex
const yBlock = new Y.Map() as YBlock;
this._yBlocks.set(id, yBlock);
yBlock.set('sys:id', id);
yBlock.set('sys:flavour', flavour);
yBlock.set('sys:version', version);
yBlock.set('sys:children', Y.Array.from(children ?? []));
...
const index = parentIndex != null
  ? parentIndex > yParentChildren.length ? yParentChildren.length : parentIndex
  : yParentChildren.length;
yParentChildren.insert(index, [id]);
```
```ts
// crud.ts :11-23 — root is DISCOVERED by scanning flavours for role==='root'; no back-pointer exists
this._yBlocks.forEach(yBlock => {
  const schema = this._schema.flavourSchemaMap.get(yBlock.get('sys:flavour'));
  if (schema?.model.role === 'root') rootId = yBlock.get('sys:id');
});
```

**Flow:** validate flavour exists AND parent accepts it (`schema.validate`) → reject duplicate id → create Y.Map → set four sys keys → merge default props from schema (`props?.(internalPrimitives)` overridden by caller props; strip `id/flavour/children`) → either flatten nested prop objects into dotted `prop:` keys or store one key per prop → append id to parent's `sys:children` (parent defaults to the discovered root for non-root blocks).

**Invariant:** (1) Children are ordered ids in the PARENT's `sys:children` array — never reorder without a transaction or undo history splits. (2) Root lookup is O(N) over all blocks on EVERY call; porters adding a cached root index must invalidate it on any add/delete. (3) `prop:`/`sys:` prefixing IS the schema — reading blocks written by another tool requires reproducing it exactly. (4) Flat mode THROWS on nested Y.Map values (`flatY2Native does not support Y.Map as value of Y.Map`, reactive/flat-native-y/initialize.ts :39) because dotted-path flattening cannot represent them.

**Probe:** `blocksuite/framework/store/src/__tests__/block.unit.spec.ts` builds blocks by hand with exactly these keys (:177-179 `yBlock.set('sys:id','0'); set('sys:flavour','page'); set('sys:children', new Y.Array())`) proving external compatibility.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-affine", query: "DocCRUD addBlock sys:id sys:flavour isFlatData", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sys:/prop: encoding and parent-side child ordering verbatim for interop; adapt id generation; omit flat-data mode if nested Y.Map values are required.
