<!-- capsule-v2 -->
# Fork vs resume state identity — when kickoff receives a persisted `id`, does the run continue that history or branch into a new one?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** How do I port "fork a flow's state" such that writes never append to the source flow's history?

## restore_from_state_id re-stamping
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (`kickoff_async` fork block :2262–2300; mutual-exclusion guard :2121–2125; `Flow.fork` classmethod :649–682; `_stamp_state_id` :2542–2546).
**Signature:** `kickoff_async(self, inputs=None, input_files=None, from_checkpoint: CheckpointConfig | None = None, restore_from_state_id: str | None = None)`.
**Data Shape:** `stored_state = self.persistence.load_state(restore_from_state_id)`; new id = `inputs.get("id") or str(uuid4())`.

### Decisive source
```python
if from_checkpoint is not None and restore_from_state_id is not None:
    raise ValueError(
        "Cannot combine `from_checkpoint` and `restore_from_state_id`. "
        "These parameters target different state systems "
        "(Checkpointing and @persist) and cannot be used together."
    )
...
    if stored_state:
        self._restore_state(stored_state)
        # Pin to inputs["id"] when provided, otherwise mint a fresh
        # UUID. NOTE: pinning inputs.id while forking shares a
        # persistence key with another flow — usually you want only
        # restore_from_state_id.
        new_state_id = (inputs.get("id") if inputs else None) or str(
            uuid4()
        )
        self._stamp_state_id(new_state_id)
        fork_succeeded = True
    else:
        ... "proceeding without hydration", ...
```
```python
# plain resume path (no fork): inputs.id REBINDS this run to stored history
if "id" in inputs and self.persistence is not None and not fork_succeeded:
    stored_state = self.persistence.load_state(restore_uuid)
```

**Flow:** guard rejects combining the two restoration systems (checkpointing vs @persist) → fork hydrates from the source UUID's latest snapshot then RE-STAMPS `state.id` fresh so subsequent `@persist` writes land under a separate persistence key → missing source id falls through SILENTLY (yellow log, baseline run) → without `restore_from_state_id`, an `inputs["id"]` is the RESUME protocol: load that uuid's snapshot, replay recorded events, set `_is_execution_resuming` only when completed methods exist.
**Invariant:** Fork ⇒ new persistence key (unless explicitly pinned via inputs.id, which in-source comments flag as history-sharing); resume ⇒ same key. Restore is single-shot per instance (`_restored_from_checkpoint` reset :2253–2256). Empty completed-set on resume means execute from scratch — the resuming flag must NOT suppress cyclic re-execution.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow_persistence.py::test_fork_with_restore_from_state_id" "lib/crewai/tests/test_flow_persistence.py::test_fork_with_pinned_state_id" "lib/crewai/tests/test_flow_persistence.py::test_restore_from_state_id_not_found_silent_fallback" "lib/crewai/tests/test_flow_persistence.py::test_fork_conflict_with_from_checkpoint_raises" -q` (expect 4 passed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "fork restore_from_state_id persistence stamp state id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the stamp-new-id-on-fork / keep-id-on-resume split and the silent-fallback posture for missing sources; adapt error handling if silent fallback is wrong for your product; omit checkpoint/@persist duality if you ship only one system. Direct tests executed green at pin.
