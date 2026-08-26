<!-- capsule-v2 -->
# JSON grid-loader shape dispatch — how does arbitrary JSON become rows/columns when the schema is unknown until the first row lands?

**Source:** DataGrip installed distribution `dist@262.9437.163` (proprietary; study/reference only); Codebase Memory `jetbrains-datagrip`. **Question:** What row-model must a streaming importer implement so ANY top-level JSON shape yields a usable table WITHOUT buffering the whole document?

## Graph-selected seam: token-dispatched dynamic-schema importer
**Path/Symbol:** `plugins/grid-loader-json/external-extensions/com.intellij.database/data/loaders/JSON.groovy` — `loadJson`:13-29, `processMapAsRows`:47-54, `processArrayAsRows`:56-69, `processArrayOfMapsAsRows`:94-108, `extractMapRow`:131-146, `getOrAllocateIdx`:148-155, `addValue`:157-160.
**Signature:** `def extractMapRow(reader, Map<String,Integer> colIdx): List`; `int getOrAllocateIdx(String name, Map colIdx)`; `dataConsumer.consumeColumns(String[] names, Class[] types)` before first `consume(Object[] row)`.
**Data Shape:** streaming Jackson parser; column registry = name→ordinal HashMap allocated in FIRST-APPEARANCE order; row values may be Jackson containers (`readValueAsTree()`) or raw text.

### Decisive source
```groovy
// JSON.groovy:17-27 — three-way top-level dispatch
switch(tok) {
  case JsonToken.START_OBJECT: processMapAsRows(reader, dataConsumer); break   // object => COLUMN STREAM
  case JsonToken.START_ARRAY:  processArrayAsRows(reader, dataConsumer); break // re-dispatch on element shape
  default:                     processValueAsRows(reader, dataConsumer); break
}
// JSON.groovy:94-108 — schema declared from FIRST ROW ONLY, then rows stream
def processor = { extractMapRow(reader, colIdx).toArray() }
def row = processor()
... colIdx.forEach { key, value ->
      addValue(names, key, value)
      addValue(types, row[value]?.getClass(), value) }
dataConsumer.consumeColumns(names.toArray(new String[0]), types.toArray(new Class[0]))
dataConsumer.consume(row)
processArrayOfXAsRows(reader, dataConsumer, processor)   // subsequent rows may ADD columns
// JSON.groovy:148-160 — sparse padding keeps ordinals dense
int getOrAllocateIdx(String name, Map<String, Integer> colIdx) {
    def idx = colIdx[name]
    if (idx == null) { idx = colIdx.size(); colIdx[name] = idx }
    return idx }
def addValue(List res, value, int idx) {
    while (res.size() < idx) res.add(null)
    res[idx] = value }
```

**Flow:** first token decides interpretation (top-level OBJECT is a stream of consume(name,value) pairs — NOT a one-row record; ARRAY re-dispatches on its first ELEMENT's token: object→dynamic-schema rows, array→positional rows, scalar→single-column rows) → array-of-maps builds schema from row #1 (names + runtime classes) and declares it via consumeColumns BEFORE emitting → later rows allocate fresh ordinals for unseen keys and null-pad holes.
**Invariant:** schema is FROZEN at first row for the declared columns, but the consumer MUST tolerate width drift — later rows can carry more cells than consumeColumns announced (getOrAllocateIdx keeps allocating). Types are per-first-row `getClass()` snapshots, not enforced coercions. Streaming end condition is `tok == null || END_ARRAY/END_OBJECT` per nesting level.
**Probe:** executed live Retrieve (2026-08-25) `search_graph { query: "extractMapRow consumeColumns schema", limit: 8 }` → extractMapRow 131-146 exact; file read whole (160L) before citing. Latent defect recorded in grid-loader-script-contract: scalar-arm processValueAsRows references undeclared `name`.
**Coverage caveat:** parse_partial file (1-160 flagged) — all ranges verified by direct read; source wins over graph.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-datagrip", query: "extractMapRow consumeColumns schema", limit: 8 });
```

## Verdict
Adopt: first-token shape dispatch (object-as-column-stream vs array-of-maps vs positional), first-row-only schema declaration with ordinal registry + null-padded sparse writes, tolerate-later-width contract. Adapt type inference (getClass snapshot) to your host's type lattice. Omit Jackson specifics; the state machine ports to any streaming parser. Pairs with grid-loader-script-contract (registration) — this capsule owns the DATA semantics.