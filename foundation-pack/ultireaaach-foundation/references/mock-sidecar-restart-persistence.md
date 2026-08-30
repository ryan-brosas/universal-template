<!-- capsule-v2 -->
# Mock-sidecar restart persistence — how should MOCK state survive a service restart without polluting the real store?

**Source:** Ultireaaach `main@60bf4a3e478022df11ed2f04077d129f4f72cc60`; Codebase Memory `ultireaaach`. **Question:** your fake backend accumulates user-created records (e.g. connected accounts) that must survive restarts, but they are mock data and must NOT enter the product database — where do they live?

## Connected graph-selected seam
**Path/Symbol:** `packages/app/src/server.ts` — `loadLiAccounts` (153-160), `saveLiAccounts` (161-166); store file derivation `LI_STORE_FILE` in the lh-backend mock plane (125-152, see lh-backend-cloud-mock for the envelope contract). Graph: search_graph "loadLiAccounts saveLiAccounts sidecar persistence linkedInAccounts" -> total 2, both functions.
**Signature:** `loadLiAccounts(): void` (mutates module globals `liAccounts`, `nextLiAccountId`); `saveLiAccounts(): void`.
**Data Shape:** JSON file `{accounts: MockLiAccount[], nextId: number}` at `ULTIREAAACH_LI_STORE` or `<db-path-minus-.db>li-accounts.json` — deliberately a sibling of the SQLite DB, not a table inside it.

### Decisive source
```ts
function loadLiAccounts(): void {
  try {
    const raw = _readFileSync(LI_STORE_FILE, "utf8");
    const parsed = JSON.parse(raw) as { accounts: MockLiAccount[]; nextId: number };
    liAccounts.push(...parsed.accounts);
    nextLiAccountId = parsed.nextId > 1 ? parsed.nextId : liAccounts.length + 1;
  } catch { /* first run: no store yet */ }        // EMPTY catch: missing OR corrupt -> silent empty
}
function saveLiAccounts(): void {
  try {
    _mkdirSync(_dirname(LI_STORE_FILE), { recursive: true });
    _writeFileSync(LI_STORE_FILE, JSON.stringify({ accounts: liAccounts, nextId: nextLiAccountId }));
  } catch (e) { console.error("[lh-mock] failed to persist li-accounts store:", e); } // log + swallow
}
```
**Flow:** module load runs `loadLiAccounts()` once (import-time effect — accounts exist before the first request); every CRUD mutation on `/lh-backend/v2/linkedInAccounts*` rewrites the whole file via `saveLiAccounts()`. On boot after a crash the mock serves whatever survived.
**Invariant:** fail-open by design — a corrupt sidecar is silently treated as "first run", so the NEXT mutation overwrites it with an empty store (silent data loss accepted because this is MOCK data; the product's real leads live in SQLite with WAL). Save failures never throw into the request path; in-memory stays source of truth. `nextId` continuity heuristic: trust the stored counter only when > 1, else derive from array length — protects id monotonicity across hand-edited files.
**Probe:** no upstream unit test covers the failure paths (coverage caveat). Deterministic evidence executed this pass: `pnpm test` exit 0 including the li-proxy suite case "POST /lh-backend/v2/linkedInAccounts persists and GET returns the account" (real-stack round-trip through saveLiAccounts/loadLiAccounts); snippet bytes matched the checkout read of server.ts 153-166.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "ultireaaach",
  qualified_name: "ultireaaach.packages.app.src.server.loadLiAccounts" });
// observed this pass: server.ts 153-160, callers 1, exact source above
```

## Verdict
Adopt the sidecar-beside-the-DB pattern whenever mocked writes must outlive the process but must stay out of the durable product schema. Adapt the file naming to your DB path convention. Watch the two deliberate traps before reusing for REAL data: the empty-catch load silently resets corrupt state, and whole-file rewrite on every mutation is O(n) per write — fine for mock scale only.
