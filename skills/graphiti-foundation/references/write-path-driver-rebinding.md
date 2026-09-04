<!-- capsule-v2 -->
# Write-path driver rebinding — why may add_episode rebind self.driver while the search decorator must clone call-scoped?

**Source:** graphiti Apache-2.0 `main@993e081a`; Codebase Memory `graphiti`. **Question:** when is mutating shared client state during a request acceptable — and what discipline must the caller already provide?

## add_episode group routing via instance-field reassignment
**Path/Symbol:** `graphiti_core/graphiti.py:add_episode` (:980-1228), rebinding block (:1073-1082); identical block in `add_episode_bulk` (:1302-1310); contrast `graphiti_core/decorators.py` (:35-62, #1659 comment + call-scoped clone); default resolution `helpers.py:get_default_group_id`.
**Data Shape:** group_id=None resolves to the provider default (`get_default_group_id` returns `'_'` for FALKORDB, `''` otherwise); an explicit id is regex-validated then compared against the CURRENT driver `_database` before any routing decision.

### Decisive source
```python
# graphiti.py :1073-1082 — write path REASSIGNS instance state:
if group_id is None:
    group_id = get_default_group_id(self.driver.provider)
else:
    validate_group_id(group_id)
    if group_id != self.driver._database:
        # if group_id is provided, use it as the database name
        self.driver = self.driver.clone(database=group_id)
        self.clients.driver = self.driver

# helpers.py get_default_group_id — provider table:
# if provider == GraphProvider.FALKORDB: return '_'   # else return ''

# decorators.py :59 — the read-side rule this contrasts with:
# Clone is call-scoped so we never reassign self.driver / self.clients.driver.
```

**Flow:** validate entity/excluded types → resolve default group id when None → explicit group_id differs from current database ⇒ validate, clone driver with database=group_id, reassign BOTH `self.driver` and `self.clients.driver` → the ENTIRE pipeline (previous-episode retrieval, extraction, dedup/resolution, saves) executes against that database → span attributes record final group_id.
**Invariant:** safe ONLY under strictly sequential episode ingestion — the docstring mandates queueing adds and awaiting each one (:1056-1059), and both server surfaces honor it (REST AsyncWorker = one serial consumer; MCP durable queue = per-group FIFO). Under concurrent adds the rebinding races other in-flight episodes onto the wrong database. Reads face the opposite world (#1659): concurrent searches with an explicit group_id queried the driver DEFAULT database and silently returned empty — hence the decorator clones per-call into kwargs instead of ever touching instance fields. Write = sequential+mutating; read = concurrent+call-scoped.
**Probe:** offline DIRECT TEST discovered pass 11 (verification pass): `pytest tests/test_handle_multiple_group_ids.py -q` → 4 passed. It pins the read-side contrast with a `_FakeDriver`: single differing group_id clones call-scoped and asserts `host.clients.driver is driver` (shared state NOT reassigned, :62-66), same-database skips the clone (:77), N=2 clones each (:89-91), non-Falkor passthrough (:102). Static write-path census: `grep -n "self.driver = self.driver.clone(database=group_id)" graphiti_core/graphiti.py` → exactly 1 hit (:1081); `self.clients.driver = self.driver` → 1 hit (:1082); decorators.py hazard comment present (:34-37). The WRITE-path rebinding itself still requires live FalkorDB to observe end-to-end (lane blocker unchanged) — coverage caveat scoped to that half only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "add_episode driver clone database group_id", limit: 10 });
```

## Verdict
Adopt the asymmetry as a documented contract: mutation-tolerant write path behind a sequential-ingestion guarantee, immutable call-scoped reads. Adapt the default-group-id table (underscore sentinel vs empty string) to your partition semantics. Omit instance reassignment entirely if your framework cannot guarantee serialization — pay the kwarg-clone cost on writes too.
