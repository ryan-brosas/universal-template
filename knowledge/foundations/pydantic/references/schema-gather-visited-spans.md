<!-- capsule-v2 -->
# `traverse_schema` visited-span memoization — how does the gatherer avoid exponential blowup on shared schema objects?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** What exactly is recorded per visited schema, and how are refs marked non-inlinable WITHOUT re-traversal?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_schema_gather.py:GatherContext.visited` (:67-84), `traverse_schema` (:118-234).
**Signature:** `def traverse_schema(schema: AllSchemas, context: GatherContext) -> None`; `visited: dict[int, tuple[int, int | None]]` keyed by `id(schema)`.
**Data Shape:** Value = `(start_span, end_span)` indices into `context.encountered_refs: list[str]`; `end=None` means "currently being traversed".

### Decisive source
```python
schema_id = id(schema)
span = context.visited.get(schema_id)
if span is not None:
    # The schema object was already traversed ... Re-traversing per path can result in exponential blowup
    # with highly interconnected models, so instead mark every definition reference encountered
    # during its traversal as non-inlinable, as if they were encountered again:
    start, end = span
    for schema_ref in context.encountered_refs[start:end]:
        context.collected_references[schema_ref] = None
    return
start = len(context.encountered_refs)
context.visited[schema_id] = (start, None)   # cycle guard: in-progress marker

... dispatch on schema['type'] into per-shape recursion (union choices, dict k/v, model fields,
    function inner schemas, serialization sub-schemas, metadata) ...

if 'serialization' in schema:
    traverse_schema(schema['serialization'], context)
traverse_metadata(schema, context)
context.visited[schema_id] = (start, len(context.encountered_refs))
```

**Flow:** record `(start, None)` BEFORE recursing (cycle detection: a `'definition-ref'` reachable from its own definition sees end=None and marks everything since start non-inlinable — inlining would create a cycle); recurse shape-by-shape; close the span. On RE-visiting an already-closed object, replay ONLY its ref-span marking them non-inlinable (`collected_references[ref] = None`) instead of walking it again.
**Invariant:** Inlining rule: a definition is inlined iff encountered exactly once overall; ANY second encounter (direct, or replayed via a shared-object span) sets the value to None. `MissingDefinitionError` raised for refs with no definition. Per-shape traversal must cover EVERY child plane (fields, computed fields, extras, tuple items, tagged-union values, chain steps, lax/strict, json/python, arguments, call return, function inner + json_input, serialization) or refs hide from the census.
**Probe:** `grep -n '\[start:end\]' pydantic/_internal/_schema_gather.py` (:127 — the span-replay loop).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "traverse_schema gathered references visited", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the id-keyed span memoization (works on any DAG of dicts where identity matters); adapt to your schema representation; omit the 3.9 match-statement TODO.
