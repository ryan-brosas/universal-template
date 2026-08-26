<!-- capsule-v2 -->
# context-lifecycle-rd-map — What is the crash-safe ordering for registering and destroying a native context?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** Which registry must be maintained alongside the context map, and in what order, so sync-resolution NIFs never touch freed memory?

## rd_map registration + rollback seam
**Path/Symbol:** `lib/quickbeam/context_worker.zig:handle_create_context` (:198-273), `handle_destroy_context` (:275-288), teardown block (:130-142).
**Signature:** `pd.rd_map: AutoHashMap(ContextId, *RuntimeData)` guarded by `pd.rd_map_mutex`; contexts map separate; entry owns embedded `rd: RuntimeData` (mutex, queue, limits) by value.
**Data Shape:** RuntimeData is address-stable storage that resolver NIFs look up BY POINTER through rd_map to deliver sync-call completions.

### Decisive source
```zig
// create: register rd BEFORE inserting into contexts, roll back on failure
pd.rd_map_mutex.lock();
pd.rd_map.put(gpa, p.context_id, &entry.rd) catch |err| {
    pd.rd_map_mutex.unlock();
    destroy_context_entry(entry);
    types.send_reply(..., @errorName(err)); return;
};
pd.rd_map_mutex.unlock();

contexts.put(p.context_id, entry) catch {
    pd.rd_map_mutex.lock(); _ = pd.rd_map.remove(p.context_id); pd.rd_map_mutex.unlock();
    destroy_context_entry(entry);
    types.send_reply(..., "Out of memory"); return;
};

// destroy: remove from rd_map FIRST
pd.rd_map_mutex.lock(); _ = pd.rd_map.remove(p.context_id); pd.rd_map_mutex.unlock();
if (contexts.fetchRemove(p.context_id)) |kv| destroy_context_entry(kv.value);

// thread shutdown: clear rd_map while holding the mutex BEFORE freeing entries
pd.rd_map_mutex.lock(); pd.rd_map.clearRetainingCapacity(); pd.rd_map_mutex.unlock();
```

**Flow:** allocate ctx → build entry (rd embedded, limits copied from pool) → install_globals → register rd in rd_map → insert into contexts (with full rollback of the previous step on OOM at each stage). Destruction reverses: rd_map first, then free.
**Invariant:** (1) Resolver NIFs hold rd_map_mutex through sync-slot publication — any window where a context id maps to freed rd is a use-after-free; hence remove-before-free on BOTH destroy and thread shutdown. (2) Every allocation failure after registration must undo the registration — the two rollback branches are load-bearing. (3) The comment "Remove externally visible RuntimeData pointers before freeing entries" documents WHY the shutdown ordering exists; porters who drop the comment drop the constraint.
**Probe:** `grep -c 'rd_map' lib/quickbeam/context_worker.zig` → 13.
**Probe:** direct test `test/core/context_pool_stress_test.exs` exercises concurrent create/destroy against this ordering.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "rd_map mutex context create destroy rollback", limit: 10 });
```

## Verdict
Adopt the two-registry discipline (pointer registry + object map) with mutex-guarded remove-before-free; adapt names; omit nothing — the ordering IS the contract. Coverage: no_recorded_issue+metadata_match; stress test executes it under concurrency.
