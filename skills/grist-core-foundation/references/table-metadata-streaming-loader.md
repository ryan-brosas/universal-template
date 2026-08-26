<!-- capsule-v2 -->
# Streaming metadata loader — how do you open a document for viewing before the data engine is up, fetching tables in parallel and pushing them downstream without flooding it?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you overlap DB fetch with engine load under a bounded-push window plus a mandatory core-schema-first gate?

## Four-state pipeline (fetch → fetched → push → pushed) gated by `startStreamingToEngine()` and a core push barrier
**Path/Symbol:** `app/server/lib/TableMetadataLoader.ts:TableMetadataLoader` (class :27–218; `_update` scheduler :177–207; `opCorePush` :140–149).
**Signature:** `new TableMetadataLoader({ decodeBuffer(buffer, tableId): TableColValues; fetchTable(tableId): Promise<Buffer>; loadMetaTables(tables, columns): Promise<any>; loadTable(tableId, buffer): Promise<any> })` — all engine/DB contact injected.
**Data Shape:** per-tableId state across four collections — `_fetches: Map<string, Promise<Buffer|null>>`, `_fetched: Set`, `_pushes: Map<string, Promise<void>>`, `_pushed: Set` — plus `_corePush`/`_corePushed`, a `_pending` counter, `_allowPushes` gate, and an unpacked cache `_tables`.

### Decisive source
```ts
private _update() {
  if (!this._allowPushes) { return; }              // pushes held until streaming starts
  const newPushes = new Set([...this._fetched]
    .filter(tableId => !(this._pushes.has(tableId) || this._pushed.has(tableId))));
  // Be careful to do the core push first, once we can.
  if (!this._corePushed) {
    if (this._corePush === undefined && newPushes.has("_grist_Tables") && newPushes.has("_grist_Tables_column")) {
      this._corePush = this._counted(this.opCorePush()).catch((e) => {
        log.warn(`TableMetadataLoader opCorePush failed: ${e}`);
      });
    }
    return;                                        // NOTHING else pushes before core schema lands
  }
  for (const tableId of [...newPushes].sort()) {   // sorted = determinism, not correctness
    if (this._pushes.size >= this._pushed.size + 3) { break; }   // ≤3 outstanding pushes
    const promise = this._counted(this.opPush(tableId));
    this._pushes.set(tableId, promise);
    promise.catch(() => {});                       // defuse unhandledRejection only
  }
}
// opFetch tolerates missing tables:
catch (err) { if (/no such table/.test(err.message)) { return null; } throw err; }
```

**Flow:** `startFetchingTable` seeds a fetch promise (once, guarded by map membership) → every operation completion calls `_update()` → until `startStreamingToEngine()` flips `_allowPushes`, buffers accumulate fetch-only → first `_update` after streaming waits until BOTH meta tables are fetched, runs the one `loadMetaTables` core push, then drains remaining fetched tables into pushes capped at `_pushed.size + 3` outstanding → `wait()` loops `Promise.all(fetches, corePush, pushes)` while `_pending > 0`; `clean()` wipes everything after wait.
**Invariant:** The engine cannot receive ANY table before `loadMetaTables(tables, columns)` completes — that's why `_grist_Tables`/`_grist_Tables_column` are marked `_pushed` inside `opCorePush` and never re-pushed ("It appears to be bad and unnecessary to send tables and columns outside of core push"). Push concurrency is 3 measured as in-flight-minus-completed. Missing tables are tolerated (historical behavior): `opFetch` swallows only "no such table", returns null, and `opPush` skips null buffers but still marks pushed. Failure of the CORE push logs a warning and does NOT throw — the doc still opens minus engine-loaded metadata. `.catch(() => {})` on push promises suppresses unhandled-rejection noise WITHOUT replacing the stored promise consumers await.
**Probe:** `test/server/lib/TableMetadataLoader.ts` — `"check flow works with typical operation order"` (:39) and `"check flow works with atypical operation order"` (:65), each looped ×5 with randomized fetch/load delays, asserting exactly which tables land in `loaded` (metatables + data tables, NOT the two meta tables) and which appear via `fetchTablesAsActions`, in both seeding orders.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "TableMetadataLoader opCorePush startStreamingToEngine", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt whenever a consumer process starts slower than its storage layer and you want view-before-ready: inject fetch/load ops, gate streaming behind an explicit start call, serialize a mandatory schema handshake first, bound in-flight loads, tolerate absent sources by exact error match. Adapt the concurrency cap (3) and the "missing table" regex to your store. Omit the sorted-iteration determinism note if your consumer has no regression-order dependence.
