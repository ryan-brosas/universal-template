<!-- capsule-v2 -->
# ToolGuard guard-merge field preservation — why must updating examples never drop generated policy code (and vice versa)?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Your admin UI patches one field of a tool guard (e.g. adds a violating example) — how do you merge the patch so generated policy code and examples never silently vanish?

## Per-tool, per-field explicit merge with existing-value defaults; omitted tools preserved entirely
**Path/Symbol:** `src/cuga/backend/cuga_graph/policy/tool_guard/tool_guard_policy_updates.py` — `merge_tool_guards(existing, incoming) -> dict[str, ToolGuard]` :11-46. Consumer: server pipeline `toolguard-pipeline.md` (persist step); direct probe `tests/unit/test_toolguard_provider.py::test_merge_tool_guards_preserves_omitted_tools_and_fields` (:412-439).
**Signature:** `merge_tool_guards(existing: Mapping[str, ToolGuard] | None, incoming: Mapping[str, Mapping[str, Any] | ToolGuard]) -> dict[str, ToolGuard]`; accepts RAW dicts or ToolGuard instances (`model_dump(exclude_unset=True)` for the latter — only explicitly-set fields participate).
**Data Shape:** `ToolGuard(violating_examples: list, compliance_examples: list, policy_code: str)` — exactly three fields; merged output rebuilt as fresh ToolGuard instances.

### Decisive source
```python
# :31-44 — every field read with existing-guard fallback
merged[tool_name] = ToolGuard(
    violating_examples=incoming_data.get("violating_examples",
        existing_guard.violating_examples if existing_guard else []),
    compliance_examples=incoming_data.get("compliance_examples",
        existing_guard.compliance_examples if existing_guard else []),
    policy_code=incoming_data.get("policy_code",
        existing_guard.policy_code if existing_guard else ""),
)
```
**Flow:** start from a copy of existing → for each incoming tool: normalize to plain dict (ToolGuard ⇒ exclude_unset dump) → build a NEW ToolGuard taking each of the three fields from incoming OR falling back to the existing guard's value (or the type default) → assign. Omitted tool names are untouched.
**Invariant:** (1) Field-level fallback is LOAD-BEARING: regenerating examples would otherwise overwrite hand/LLM-generated `policy_code` (and re-generating code would wipe curated examples) — the docstring states both directions. (2) Whole-object replacement is WRONG here even when the caller sends full ToolGuards — `exclude_unset` keeps partial-instance patches safe. (3) Rebuild as new instances (never mutate cached policy objects in place) so runtime caches see clean swaps.

**Probe:** `tests/unit/test_toolguard_provider.py::test_merge_tool_guards_preserves_omitted_tools_and_fields` (:412-439).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "merge_tool_guards violating_examples compliance_examples policy_code", limit: 8 });
```
## Verdict
Adopt this exact three-field merge shape for any persisted artifact where generation and curation interleave (examples + code). Generalize by listing your own fields explicitly — reflection-based merging would reintroduce the drop bug.
