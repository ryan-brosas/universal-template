<!-- capsule-v2 -->
# Project mutation lock — how do N independent processes serialize writes per project, with a global stop-the-world?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What lock protocol lets per-project writers proceed concurrently but still allow one wildcard actor to freeze every project?

## Set-SH/member-EX two-key protocol
**Path/Symbol:** `src/daemon/project_lock.c:project_lock_acquire_internal` (109–152).
**Signature:** `cbm_private_file_lock_status_t cbm_project_lock_acquire(mgr, project, deadline_ms, cancel_token, cbm_project_lock_lease_t **out);` (+ `cbm_project_lock_try_acquire`)
**Data Shape:** Lease holds TWO native locks. Key grammar: `"cbm-project-v1:<lowercased-name>"` per project; shared set key `"cbm-project-set-v1"`. Wildcard `"*"` takes the SET in EX and skips the member key. Keys are case-folded so "Foo"/"foo" alias to one lease.

### Decisive source
```c
status = try_once ? cbm_lock_registry_try_acquire(registry, PROJECT_SET_KEY,
             wildcard ? EX : SH, &lease->project_set)
                  : cbm_lock_registry_acquire   (registry, PROJECT_SET_KEY,
             wildcard ? EX : SH, deadline_ms, cancel_token, &lease->project_set);
if (status != OK) return project_lock_failed_acquire(lease, status, lease_out);
if (!wildcard) { /* then take member key in EX ... same failure rollback */ }
```

**Flow:** acquire set-key SH (writers coexist) → acquire project-key EX → mutate → release. A wildcard maintenance actor takes the SET exclusively, which blocks ALL new per-project leases; conversely any live project EX blocks the wildcard. Failure at step 2 rolls back step 1 (`project_lock_failed_acquire`), and release order is project-then-set with IO-propagation.
**Invariant:** Every mutation of one project's DB must hold that project's EX; the two-key handshake is atomic-ish only because failed acquires always roll back partial leases — never skip the rollback.
**Probe:** `tests/test_project_lock.c:project_lock_coordinates_instances_projects_wildcard_and_case_aliases` (Foo blocks foo; bar proceeds under Foo's lease; "*" excludes even "unrelated").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_project_lock_lease_release", limit: 5 });
```

## Verdict
Adopt the SH-set/EX-member reader-writer shape for any multi-resource registry; adapt key naming/folding to your namespace; omit the native-lock backend details if your platform offers fcntl-style shared locks directly.
