<!-- capsule-v2 -->
# narrow_type registry — best-effort promotion of message parts with kind-stripping on failure

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** How do base wire parts become typed subclasses on replay WITHOUT breaking round-trips when the claim doesn't hold?

## _narrow_call / _narrow_return
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/messages.py:_narrow_call` (:2364-2375), `_narrow_return` (:2378-2395), registries `_TOOL_CALL_NARROWERS/_TOOL_RETURN_NARROWERS/_NATIVE_CALL_NARROWERS/_NATIVE_RETURN_NARROWERS` (:2349-2357), `parse_tool_kind` (:1275-1282).
**Signature:** `narrow_type(part, *, tool_kind: ToolPartKind | None = None) -> SamePartClass`; narrower registry `dict[str, Callable[[Part], Part]]` keyed by `tool_kind ∈ {'tool-search', 'capability-load'}`.
**Data Shape:** Parts carry optional `tool_kind` discriminator; typed subclasses pin it to a Literal and shadow `args`/`content` with TypedDicts; deserialization auto-promotes via a callable discriminator consulting `_TYPED_PART_TAGS[(part_kind, tool_kind)]`.

### Decisive source
```python
# messages.py:2364-2375 — best-effort by contract: no claim → same object; bad claim → strip kind
def _narrow_call(part, narrowers, tool_kind):
    kind = tool_kind if tool_kind is not None else part.tool_kind
    narrower = narrowers.get(kind) if kind is not None else None
    if narrower is None:
        return part
    try:
        return narrower(part)
    except pydantic.ValidationError:
        return replace(part, tool_kind=None) if part.tool_kind is not None else part

# messages.py:2386-2395 — returns additionally restructure JSON-string content first,
# but only rebuild when parsing actually changed something (identity preserved otherwise)
structured = part.structured_content()
narrow_input = (
    replace(part, content=structured) if structured is not None and structured is not part.content else part
)
```

**Flow:** Producers stamp `tool_kind` at emission (`_parts_manager`, deferred-capability loader); on replay/UI ingestion `narrow_type(part)` looks up the registered promoter → validates shape against the subclass → promotes, or STRIPS an unsubstantiated kind from the base part. Why stripping matters: a base part retaining a claim would route back to the typed subclass through the deserialization discriminator and fail validation on reload — stripping keeps history dump/load-stable. Dispatch is by KIND, never tool_name, so user tools that happen to share our names never get mis-promoted.
**Invariant:** Promotion NEVER raises — invalid data yields either the untouched original (kwarg-only claim) or a kind-stripped copy. Registration happens at import time in sibling modules late-imported by `messages.py`; adding a family requires: subclasses + narrower registration + discriminated-union membership + tag entries (documented recipe at NativeToolCallPart :2299-2322).
**Probe:** `tests/test_messages.py::test_narrow_type_leaves_claim_free_part_unchanged_on_invalid_data` (:2235), `::test_narrow_type_strips_unsubstantiated_tool_kind_set_on_part` (:2256), `::test_narrow_type_upgrades_json_string_content` (:2292), `::test_stripped_tool_kind_part_survives_roundtrip` (:2306).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "narrow_type tool_kind narrowers ToolCallPart promote", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt best-effort promotion with kind-stripping (never raising) and kind-based dispatch; adapt the discriminator/tag plumbing to your serializer; omit the JSON-string restructure branch if your UI layer transmits structured content only. Caveat: source read at HEAD this session.
