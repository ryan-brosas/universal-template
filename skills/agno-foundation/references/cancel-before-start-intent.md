<!-- capsule-v2 -->
# Cancel-before-start intent — How does cancellation survive the race where cancel() arrives before register()?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** When cancel_run fires before the run registers itself, why isn't the cancellation lost?

## setdefault preserves intent written before registration
**Path/Symbol:** `libs/agno/agno/run/cancellation_management/in_memory_cancellation_manager.py:InMemoryRunCancellationManager.register_run/cancel_run/is_cancelled/cleanup_run` (:19-95).
**Signature:** `register_run(run_id: str) -> None`; `cancel_run(run_id: str) -> bool`; `is_cancelled(run_id: str) -> bool`; `cleanup_run(run_id: str) -> None`.
**Data Shape:** `_cancelled_runs: Dict[str, bool]` guarded by a `threading.Lock`; a parallel `_member_runs: Dict[str, Set[str]]` maps team-run → member run_ids for cancel cascade; every method has an `a*` twin using a dedicated `asyncio.Lock`.

### Decisive source
```python
def register_run(self, run_id: str) -> None:
    """Uses setdefault to preserve any existing cancellation intent
    (cancel-before-start support for background runs)."""
    with self._lock:
        self._cancelled_runs.setdefault(run_id, False)

def cancel_run(self, run_id: str) -> bool:
    """Always stores cancellation intent, even for runs not yet registered."""
    with self._lock:
        was_registered = run_id in self._cancelled_runs
        self._cancelled_runs[run_id] = True
        return was_registered

def is_cancelled(self, run_id: str) -> bool:
    with self._lock:
        return self._cancelled_runs.get(run_id, False)
```

**Flow:** background runs are created before they execute, so cancel may arrive first — `cancel_run` writes True for an unknown id instead of ignoring it; when the run later calls `register_run`, `setdefault(run_id, False)` does NOT overwrite the stored True; the first `raise_if_cancelled` inside the run loop then raises `RunCancelledException` immediately.
**Invariant:** register must be a NON-destructive insert (setdefault), never an assignment. The naive `self._cancelled_runs[run_id] = False` erases pre-registration intent and the zombie run runs to completion unkillable. cleanup deletes the key only on completion; `cancel_run`'s bool return distinguishes "marked running run" from "stored intent".
**Probe:** `grep -c 'setdefault(run_id, False)' libs/agno/agno/run/cancellation_management/in_memory_cancellation_manager.py` → **2** (sync + async twins); direct behavior test `libs/agno/tests/integration/agent/test_agent_run_cancellation.py::test_cancel_agent_during_sync_streaming` and `::test_cancel_agent_sync_streaming_preserves_content_in_db`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "InMemoryRunCancellationManager cancel_before_start register", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the intent-preserving state machine verbatim (it is three dict ops under a lock); adapt lock type to your runtime (single event loop can drop threading.Lock); omit member-run cascade if you have no team orchestration.
