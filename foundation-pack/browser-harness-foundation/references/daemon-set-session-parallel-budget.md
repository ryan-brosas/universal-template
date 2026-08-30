<!-- capsule-v2 -->
# Parallel session-budget choreography — how does a tab switch stay under a 5s IPC timeout while re-arming four CDP domains?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** After switching tabs, why must old-session teardown and new-session domain enables run as one parallel gather — and what stays synchronous vs fire-and-forget?

## gather(disable_old ∥ enable×4) + cosmetic-marker off the sync path
**Path/Symbol:** `src/browser_harness/daemon.py:handle` set_session branch (:588-624) + `_enable_default_domains` (:470-492).
**Signature:** `set_session{session_id, target_id?}` → `{"session_id"}`; `_enable_default_domains(session_id)` gathers Page/DOM/Runtime/Network.
**Data Shape:** fresh CDP sessions start with ALL domains disabled; each enable wrapped in its own `asyncio.wait_for(timeout=4)` with per-domain error swallow.

### Decisive source
```python
async with self._session_state_lock:
    old_session = self.session; ...
tasks = []
if old_session and old_session != new_session:
    async def disable_old():
        try: await asyncio.wait_for(
            self.cdp.send_raw("Network.disable", session_id=old_session), timeout=2)
        except Exception: pass
    tasks.append(disable_old())          # defense in depth ONLY — the real
                                         # gate is consumer-side filtering
tasks.append(self._enable_default_domains(new_session))
await asyncio.gather(*tasks)             # different sessions = independent
                                         # requests; sequential ≈ 22s worst case
# 🐴 title marker is purely cosmetic — fire-and-forget so it never adds
# to the synchronous IPC budget
asyncio.create_task(_silent(asyncio.wait_for(...Runtime.evaluate(mark_js)..., 2)))
```

**Flow:** swap identity fields under lock → parallel [old Network.disable ∥ 4 new enables] → reply → background marker. Initial attach runs the same four-enable gather (`test_set_session_first_attach_runs_four_enables_in_parallel`).
**Invariant:** without per-session Network.enable, helpers depending on Network events (notably `wait_for_network_idle`) silently stop working after every tab switch; without the gather, five sequential round trips blow the helper's 5s socket read timeout. Consumer-side session filtering remains the correctness gate for idle detection — daemon disable is hygiene.
**Probe:** `tests/unit/test_daemon.py:26` four-enables-on-new-session; `:93` disables-old-before/parallel-with-new; `:125` no-disable-when-no-previous-session; `:144` disable+enables-in-parallel; `:70` per-domain error swallow.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "set_session enable default domains parallel", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the budget-driven split (identity under lock → parallel I/O → reply → cosmetics deferred) for any RPC layer pinned by a client read timeout; adapt domain lists/timeouts; omit CDP method names. Five tests pin it.
