<!-- capsule-v2 -->
# Weakref agent backrefs with release — how do run items reference their agent without pinning it in memory?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory project `openai-agents-python`. **Question:** Every RunItem carries the Agent that produced it; how does that stay true after GC without leaking whole agent graphs per item?

## Lazy weakref attribute protocol
**Path/Symbol:** `src/agents/items.py`: `RunItemBase` `_agent_ref` field + `__post_init__` (:108–121), `__getattribute__` override intercepting `"agent"` (:118–121), `release_agent()` (:123–132), resolver `_get_agent_via_weakref` (:134–149), missing-attr sentinel `_MISSING_ATTR_SENTINEL = object()` (:92–93); `HandoffOutputItem` extends the same protocol to `source_agent`/`target_agent` (:324–364).
**Signature:** `def _get_agent_via_weakref(self, attr_name: str, ref_name: str) -> Any`.
**Data Shape:** dataclass keeps its STRONG slot (`agent`) for repr/asdict compatibility but sets it to None on release; a parallel `_agent_ref: weakref.ReferenceType | None` holds the live handle.

### Decisive source
```python
# (:135-137) Preserve the dataclass field so repr/asdict still read it, but lazily resolve
# the weakref when the stored value is None (meaning release_agent already dropped the
# strong ref). If the attribute was never overridden we fall back to the default descriptor chain.
value = data.get(attr_name, _MISSING_ATTR_SENTINEL)
if value is _MISSING_ATTR_SENTINEL: return object.__getattribute__(self, attr_name)
if value is not None: return value
ref = object.__getattribute__(self, ref_name)
if ref is not None:
    agent = ref()
    if agent is not None: return agent
return None   # agent was garbage-collected: honest None, not a crash
```

**Flow:** construct (strong ref + weakref) → readers hit `__getattribute__` → strong value returned while alive → after `release_agent()` the strong slot is None and every read resolves through the weakref → dead agent ⇒ transparently None. Sentinel distinguishes "slot never touched" from "explicit None" so subclasses without the field still work.
**Invariant:** Serialization/repr must keep working AFTER release (field preserved as None, never deleted) — deleting the attribute breaks dataclass machinery. Callers must tolerate None post-release; identity-based logic (e.g. ownership relinks) must run BEFORE release.
**Probe:** `grep -n '_MISSING_ATTR_SENTINEL' src/agents/items.py` → 2 hits (def :93, use :140). Direct tests: `tests/test_result_cast.py::test_run_result_streaming_release_agents_uses_weakref_until_agent_is_collected` (:233), `tests/test_agent_memory_leak.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "release_agent weakref _agent_ref get_agent_via_weakref", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt weakref-backref-with-release for any long-lived item graph pointing at heavy parents; adapt to non-dataclass languages by preserving the "keep-the-slot-null-it" rule; omit the handoff twin if you lack multi-agent handoffs.
