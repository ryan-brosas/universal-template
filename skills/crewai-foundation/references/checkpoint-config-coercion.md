<!-- capsule-v2 -->
# Checkpoint config coercion — True→config BeforeValidator with handler-registration side effect

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** How does a boolean field (`checkpoint=True`) expand into a full provider config — and why must validation trigger listener registration?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/state/checkpoint_config.py` — `_coerce_checkpoint` (:146), `CheckpointConfig` (:160), `apply_checkpoint` (:215); registration in `state/checkpoint_listener.py:_ensure_handlers_registered`.
**Signature:** `_coerce_checkpoint(v: Any) -> Any` (pydantic BeforeValidator on Crew/Flow/Agent checkpoint fields); `apply_checkpoint(instance, from_checkpoint) -> Any | None` (restored instance or None).
**Data Shape:** `CheckpointConfig(location="./.checkpoints", on_events=["task_completed"]|"*", provider=JsonProvider|SqliteProvider (discriminated), max_checkpoints=None, restore_from=None)`.

### Decisive source
```python
# :146 the whole trick: bools become configs INSIDE pydantic validation
def _coerce_checkpoint(v: Any) -> Any:
    if v is True:
        v = CheckpointConfig()
    if isinstance(v, CheckpointConfig):
        from crewai.state.checkpoint_listener import _ensure_handlers_registered
        _ensure_handlers_registered()
    return v

# :196 model_validator backs up the same invariant for direct construction
@model_validator(mode="after")
def _register_handlers(self) -> CheckpointConfig:
    from crewai.state.checkpoint_listener import _ensure_handlers_registered
    if isinstance(self.provider, SqliteProvider) and not Path(self.location).suffix:
        self.location = f"{self.location}.db"     # sqlite needs A FILE
    _ensure_handlers_registered()
    return self

# :215 restore routing at kickoff
if from_checkpoint.restore_from is not None:
    restored = type(instance).from_checkpoint(from_checkpoint)
    restored.checkpoint = from_checkpoint.model_copy(update={"restore_from": None})
    return restored      # caller dispatches into ITS kickoff on this instance
```

**Flow:** user sets `checkpoint=True` (or dict/config) → BeforeValidator expands + registers event-bus handlers so subsequent task_completed/`*` events write checkpoints → kickoff receives `from_checkpoint`: with `restore_from` it builds a fresh instance via classmethod `from_checkpoint`, CLEARS restore_from on the copy, and hands back control; without, it just attaches config to the running instance.
**Invariant:** Registration MUST happen at validation time, not kickoff time — events fire during construction/kickoff before any explicit setup call. SqliteProvider location gets `.db` appended only when suffix-less (a path like `./ck/dir` stays a dir → broken provider). Restore clears `restore_from` on the restored copy or the next kickoff would re-restore forever.
**Probe:** `grep -c '_ensure_handlers_registered' lib/crewai/src/crewai/state/checkpoint_config.py` → `4`; `grep -c 'def test_crew_true' lib/crewai/tests/test_checkpoint.py` → `1`.
**Direct test:** `tests/test_checkpoint.py::test_none_returns_none/:40 false_sentinel/:43 true_config/:48 config_passthrough`, `::test_crew_true` (:67), `::test_agent_config_overrides_crew` (:83).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "_coerce_checkpoint converts True to CheckpointConfig", limit: 5 });
// → ext-crewAI...state.checkpoint_config._coerce_checkpoint Function 146-157
```

## Verdict
Adopt validate-time coercion + side-effectful registration + restore-clears-itself for declarative durability flags. Adapt provider discrimination to host storage. Omit CrewAI's JsonProvider pruning internals.
