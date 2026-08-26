<!-- capsule-v2 -->
# mkstemp staging — why is a predictable staging filename a security bug?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What attack does `O_EXCL` staging creation close that `<db>.stage.<pid>.<counter>` left open?

## Unpredictable exclusive creation, no unlink-first
**Path/Symbol:** `src/pipeline/pipeline.c:create_staging_path` (2370–2406) with the threat-model comment at the publish call site (1675–1685).
**Signature:** `static char *create_staging_path(const char *final_path);` — suffix `".stage.XXXXXX"` via `cbm_mkstemp`.
**Data Shape:** Returns a malloc'd path with a mkstemp-minted suffix; fd closed immediately after creation (file used as the dump target). Windows variant caps input length exactly rather than truncating.

### Decisive source
```c
/* The staging name must be unpredictable and created exclusively. It used to be
 * "<db>.stage.<pid>.<counter>", which any other process can compute in advance;
 * this path is then unlinked and written, so in a world-writable database
 * directory an attacker could land a symlink in the window between the two and
 * have us clobber the target. Sharing the mkstemp-based helper ... closes that:
 * O_EXCL creation means we only ever write a file we made ourselves.
 * The old unlink-first step goes with it: a freshly minted name cannot collide,
 * and its sidecars cannot pre-exist either. */
```

**Flow:** publish → create_staging_path mints unique name (no pre-unlink) → dump graph into it → seal + atomic rename onto final; discard paths unlink the stage we created.
**Invariant:** Never compute-then-unlink-then-write a shared-directory path; exclusivity at creation is what defeats symlink landing.
**Probe:** covered by publish-path tests (`tests/test_pipeline.c:pipeline_closure_repair_*` exercise create/discard legs) plus security suite posture.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "create_staging_path", limit: 5 });
```

## Verdict
Adopt mkstemp-style staging for any temp file in shared directories; adapt suffix conventions; nothing to omit — remove any unlink-first patterns you find.
