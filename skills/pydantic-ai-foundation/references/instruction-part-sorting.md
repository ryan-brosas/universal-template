<!-- capsule-v2 -->
# Instruction part ordering — why do static instructions sort ahead of dynamic ones, and when does joining produce None?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How are structured instruction parts ordered and rendered so provider prompt caching can hold a static prefix?

## `InstructionPart.join` / `InstructionPart.sorted`
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/messages.py:InstructionPart` (:1744–1780): fields `content: str`, `dynamic: bool = False`, `part_kind='instruction'`; `join` (:1770–1773), `sorted` (:1775–1778). Consumers: `Model.prepare_request` appends prompted-output instructions then sorts (:656–661); `Model._get_instruction_parts` synthesizes parts for direct `model.request()` callers (:913–948).
**Signature:** `join(parts: Sequence[InstructionPart]) -> str | None`; `sorted(parts: Sequence[InstructionPart]) -> list[InstructionPart]`.
**Data Shape:** `join` returns `'\n\n'.join(p.content for p in parts).strip() or None` — whitespace-only input collapses to `None`. `sorted` is Python's stable sort keyed on `p.dynamic`, so False < True with original relative order preserved within each class.

### Decisive source
```python
# messages.py:1775-1778 — stable two-class sort; static prefix first
@staticmethod
def sorted(parts: Sequence[InstructionPart]) -> list[InstructionPart]:
    """Sort instruction parts with static (dynamic=False) before dynamic, preserving relative order."""
    return sorted(parts, key=lambda p: p.dynamic)
```

**Flow:** static literals from `Agent(instructions=...)` carry `dynamic=False`; functions/templates/toolset `get_instructions()` carry `dynamic=True` → any composition point (e.g. appending prompted-output instructions) funnels through `sorted` → render via `join` into the request's single `instructions` string, `None` when nothing survived. Model implementations use the flag for caching decisions: Anthropic prompt caching holds the static prefix while dynamic instructions ride uncached behind it.

**Invariant:** The sort must be STABLE — dynamic parts arrive in registration/emission order and that order is semantic (later toolsets append later); a plain unstable reorder would shuffle toolset-authored guidance between runs. Static-before-dynamic is what makes the cached prefix possible: interleaving a dynamic part among statics splits the cacheable region. Empty-to-None collapse keeps 'no instructions' distinct from 'empty string instructions' on the wire.

**Probe:** `tests/test_messages.py::test_instruction_part_sorted_and_join` pins stable ordering (interleaved inputs, order preserved per class) and the whitespace→None collapse.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "InstructionPart join sorted instruction_parts prepare_request", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the stable two-class sort and the join-to-None collapse wherever instructions compose from mixed-provenance parts. Adapt the flag's producers (whatever your dynamic-instruction sources are). Omit the OTel rendering of instruction parts — covered by instrumentation settings, not a porting question here.
