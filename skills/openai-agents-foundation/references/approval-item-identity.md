<!-- capsule-v2 -->
# ToolApprovalItem identity equality — why must two approvals for the same call stay distinct objects?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory project `openai-agents-python`. **Question:** If approvals were value-compared, what exactly breaks in a turn that emits several approval requests — even for the same tool with identical arguments?

## Identity hash/equality by design
**Path/Symbol:** `src/agents/items.py`: `ToolApprovalItem` (:556–683) — `__hash__` (:616–618) and `__eq__` (:620–622); `__post_init__` derives `tool_name`/`tool_namespace`/`tool_lookup_key` from the raw item when absent (:585–614).
**Signature:** `def __hash__(self) -> int: return object.__hash__(self)`; equality is `self is other`.
**Data Shape:** fields: `raw_item`, `tool_name`, `_allow_bare_name_alias`, literal `type="tool_approval_item"` (kept 3rd to preserve the historical positional constructor `(agent, raw_item, tool_name, type)`), `tool_namespace`, `tool_origin`, `tool_lookup_key`.

### Decisive source
```python
def __hash__(self) -> int:
    """Hash by object identity to keep distinct approvals separate."""
    return object.__hash__(self)

def __eq__(self, other: object) -> bool:
    """Equality is based on object identity."""
    return self is other
```

**Flow:** every emitted approval request is its own ledger entry keyed by object identity; sets/dicts of pending interruptions therefore hold N distinct entries even when raw items share `(name, arguments)` or even `call_id`. Derived display helpers (`qualified_name` collapses synthetic deferred namespaces :637–642; `arguments` falls back through `arguments → params → input` and stringifies non-str :644–665; `_extract_call_id` prefers `call_id` then `id` :667–671) never participate in identity. `to_input_item()` RAISES (:678–683) — an approval item must be filtered out of model input, never converted.
**Invariant:** Approval granularity is per-occurrence. Value-based hashing (e.g. hashing `(tool_name, call_id)`) would silently collapse two same-call_id approvals into one ledger entry — one human decision would answer both, and rejection would leak across occurrences.
**Probe:** `grep -n 'object.__hash__(self)' src/agents/items.py` → exactly 1 hit at :618. Behavior pinned by the interruption-ledger suites (`tests/test_run_internal_approvals.py`, `tests/test_tool_approval_call_id_reuse.py`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "ToolApprovalItem hash identity interruption", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt identity-keyed approval items plus the derived-field accessors; adapt field derivation to your raw-item vocabulary; omit the Responses-specific namespace/lookup-key shapes if you have no namespaced tools. Deliberately distinct from the dedup-gate capsule (that one fails loud on call-id REUSE by the model; this one keeps same-payload approvals separate).
