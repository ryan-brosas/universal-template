<!-- capsule-v2 -->
# Export ActiveDocSource seam — how does grist decouple exporters from ActiveDoc so the same export code runs on a worker thread?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the minimal data-access contract an exporter needs, and how does its direct implementation wrap ActiveDoc so a worker thread can request the same data over a MessagePort?

## The port boundary: three methods, plain-data in/out
**Path/Symbol:** `app/server/lib/Export.ts` — `interface ActiveDocSource` (:31–35), direct implementation `class ActiveDocSourceDirect` (:38–51), session bridging helper `docSessionFromRequest` (imported from `app/server/lib/DocSession`, used at :46/:48).
**Signature:** `getDocName(): Promise<string>`; `fetchMetaTables(): Promise<TableDataActionSet>`; `fetchTable(tableId: string): Promise<TableDataAction>`.
**Data Shape:** everything crossing the boundary is plain data (`TableDataActionSet` / `TableDataAction` = `[null, null, rowIds, dataByColId]` chunks) — deliberately MessagePort-serializable, because `workerExporter.ts` consumes the SAME interface through a grain-rpc stub (`rpc.getStub<ActiveDocSource>("activeDocSource")`, workerExporter.ts:28).

### Decisive source
```ts
// Interface to document data used from an exporter worker thread (workerExporter.ts). Note that
// parameters and returned values are plain data that can be passed over a MessagePort.
export interface ActiveDocSource {
  getDocName(): Promise<string>;
  fetchMetaTables(): Promise<TableDataActionSet>;
  fetchTable(tableId: string): Promise<TableDataAction>;
}

// Implementation of ActiveDocSource using an ActiveDoc directly.
export class ActiveDocSourceDirect implements ActiveDocSource {
  private _req: RequestWithLogin;

  constructor(private _activeDoc: ActiveDoc, req: express.Request) {
    this._req = req as RequestWithLogin;
  }

  public async getDocName() { return this._activeDoc.docName; }
  public fetchMetaTables() { return this._activeDoc.fetchMetaTables(docSessionFromRequest(this._req)); }
  public async fetchTable(tableId: string) {
    const { tableData } = await this._activeDoc.fetchTable(docSessionFromRequest(this._req), tableId, true);
    return tableData;
  }
}
```
**Invariant:** the third argument `true` on `_activeDoc.fetchTable` is what keeps exports OFF the formula engine path (raw rendered values, no recalculation round-trip) — a porter who drops it silently changes export semantics under formula-heavy docs. Auth identity travels inside the captured `RequestWithLogin`: every fetch the worker triggers is permission-checked against the ORIGINAL requester even though the call originates off-thread.

**Flow:** `Export.ts` exposes two adapter constructors — `exportTable(activeDoc, tableRef, req)` → `doExportTable(new ActiveDocSourceDirect(...))` (:190–197) and `exportSection(...)` → `doExportSection(new ActiveDocSourceDirect(...))` (:278–289) — while `ExportXLSX.streamXLSX` registers ONE `ActiveDocSourceDirect` instance as rpc impl `"activeDocSource"` for the worker pool (ExportXLSX.ts:56). Every downstream miner (`doExportDoc`/`doExportTable`/`doExportSection`) is written against the interface, never against `ActiveDoc`, which is exactly why XLSX could be moved to worker threads without touching the data-selection logic. Whole-doc export `doExportDoc(activeDocSource, handleTable)` (:171–185) iterates `_grist_Tables.filterRowIds({summarySourceTable: 0})`, skipping censored tables, calling `handleTable(data)` per raw table — the streaming hook the worker uses to emit sheet-by-sheet.

**Probe:** deterministic greps (no dedicated unit suite for this plane — coverage caveat):
```bash
cd /mnt/hdd/utopia/inspo/grist-core
grep -n "export interface ActiveDocSource" app/server/lib/Export.ts          # 31
grep -n "class ActiveDocSourceDirect implements ActiveDocSource" app/server/lib/Export.ts  # 38
grep -n "fetchTable(docSessionFromRequest(this._req), tableId, true)" app/server/lib/Export.ts  # 48
```
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "doExportDoc activeDocSource handleTable", limit: 5 });
// → Export.doExportDoc Function app/server/lib/Export.ts 171-185; Export.ActiveDocSource Interface 31-35
```

## Verdict
Adopt the three-method source-interface pattern verbatim for any "big object in the host process, hungry consumer in a worker" split: name the interface after the ROLE (a data source), keep every signature plain-data, capture auth/request context in the direct implementation, and register exactly one instance over RPC. Adapt method names to your domain; omit the `fetchTable(…, true)` raw-mode flag only if your engine has no lazy-recalculation semantics to bypass — but document that decision, because grist's flag encodes "export sees committed values".
