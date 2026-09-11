<!-- capsule-v2 -->
# Tombstone-delete rollback latch — how do you roll back a transaction when the failure happens OUTSIDE the try that owns it?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** The transaction begins early, but permission checks and helper failures can throw from code paths not lexically inside one try — where does rollback live so no open transaction ever leaks?

## Pre-declared sentinel + rollback in EVERY except arm
**Path/Symbol:** `backend/python/app/api/routes/agent.py:delete_agent` (:2926–3044).
**Signature:** `txn_id: str | None = None; services = None` declared BEFORE any await that can raise.
**Data Shape:** Soft delete only — `delete_agent()` marks `isDeleted`; toolsets/tools/knowledge deliberately remain (the response's deleted-counts are hardcoded zeros).

### Decisive source
```python
async def delete_agent(request: Request, agent_id: str) -> JSONResponse:
    txn_id = None          # sentinel declared BEFORE anything can raise
    services = None
    try:
        ...
        txn_id = await services["graph_provider"].begin_transaction(read=[...], write=[...])
        result = await services["graph_provider"].delete_agent(agent_id, user_doc["_key"], org_key, transaction=txn_id)
        if not result:
            if txn_id is not None:
                await services["graph_provider"].rollback_transaction(txn_id)
            raise HTTPException(status_code=500, detail="Failed to delete agent")
        await services["graph_provider"].commit_transaction(txn_id)
        # post-commit side effects (token-refresh cancellation) stay best-effort
    except HTTPException:
        if txn_id is not None and services is not None:
            try:
                await services["graph_provider"].rollback_transaction(txn_id)
            except Exception as rb_err:
                services["logger"].warning(f"⚠️ Failed to rollback transaction {txn_id}: {rb_err}")
        raise                                   # original error preserved
    except Exception as e:
        if txn_id is not None and services is not None:
            try:
                await services["graph_provider"].rollback_transaction(txn_id)
            except Exception as rb_err:
                ...                              # logged, never re-raised
        raise HTTPException(status_code=400, detail=str(e)) from e
```

**Flow:** declare sentinels → permission checks → begin → soft-delete inside txn → on falsy result: explicit rollback THEN raise → commit → post-commit side effects wrapped in their own swallow-and-log. Both outer except arms independently attempt rollback if (and only if) the id is still set.
**Invariant:** Rollback is attempted at every exit point a failure can reach — including exceptions raised before `begin_transaction` even runs (guarded by the `None` check), and including an explicit mid-try rollback followed by raise (the second rollback attempt hits the `is not None` guard only because this route does NOT null the id after its manual rollback — the provider-side abort makes the retry harmless). Rollback failures are warnings, never masks.
**Probe:** No unit test pins the double-arm ladder (route-level seam) — coverage caveat recorded; deterministic check = sentinel-before-first-await + rollback present in both except arms of the source above.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "delete_agent rollback_transaction tombstone", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sentinel-latch pattern (`txn_id = None` before first await; every except arm guards-and-rolls-back; rollback errors never mask originals). Adapt which side effects run post-commit (PipesHub cancels ETCD-backed token-refresh tasks for service-account agents). Omit the ArangoDB-specific collection lock lists.
