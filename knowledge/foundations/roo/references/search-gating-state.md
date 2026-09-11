<!-- capsule-v2 -->
# Search gating + state machine — when is a vector search allowed, and who may flip Indexing back?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** What preconditions gate `searchIndex`, and how does the status machine avoid Stopping being overwritten?

## Indexed-or-Indexing gate; progress can never override Stopping
**Path/Symbol:** `src/services/code-index/search-service.ts:searchIndex` (:27-64); `src/services/code-index/state-manager.ts` (:58-81 Stopping guard).
**Signature:** `searchIndex(query: string, directoryPrefix?: string): Promise<VectorStoreSearchResult[]>`; states = Standby | Indexing | Indexed | Error | Stopping.
**Data Shape:** minScore resolution ladder: user setting → model-specific `scoreThreshold` from the registry → global default; maxResults likewise.

### Decisive source
```ts
const currentState = this.stateManager.getCurrentStatus().systemStatus
if (currentState !== "Indexed" && currentState !== "Indexing") { throw ... } // search DURING indexing allowed
// state-manager, both progress reporters:
if (this._systemStatus === "Stopping") return   // never override a user stop with progress
```

**Flow:** feature-enabled AND configured gates first → embed the QUERY (single text) → normalize prefix (path.normalize only — the segment grammar lives in the store layer) → store search. Any thrown error flips the manager to Error("Search failed: …") then re-THROWS — callers see failures, UI sees state. State manager resets progress counters on every non-Indexing transition and supplies default messages for Standby/Indexed/Error.
**Invariant:** allowing search during Indexing means results are best-effort under an incomplete marker — porters must NOT tighten this to Indexed-only without accepting dead search windows during long scans. The Stopping latch prevents a late batch-progress callback from resurrecting "Indexing" after the user pressed stop.
**Probe:** `src/services/code-index/__tests__/manager.spec.ts`; executed pins: gate expression :36, Stopping guard ×2 (:62/:87), minScore ladder (:525-535).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "searchIndex currentSearchMinScore setSystemState Stopping", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt the two-state search gate and the Stopping latch in any progress reporter. Adapt default messages. Omit i18n plumbing. Coverage caveat: state-manager has no dedicated spec — pinned by source read + executed greps.
