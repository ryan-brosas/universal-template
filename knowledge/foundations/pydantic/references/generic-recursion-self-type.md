<!-- capsule-v2 -->
# `generic_recursion_self_type` — how are recursive generics turned into schema refs without infinite recursion?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** What is the exact enter/exit discipline of the recursion cache, and when does it yield a placeholder instead of recursing?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_generics.py:generic_recursion_self_type` (:410-439), `recursively_defined_type_refs` (:442-447).
**Signature:** `@contextmanager def generic_recursion_self_type(origin: type[BaseModel], args: tuple[Any, ...]) -> Generator[PydanticRecursiveRef | None]`.
**Data Shape:** State lives in a `ContextVar[set[str] | None]` (`_generic_recursion_cache`, default None) — per-context, not global; members are string type-refs.

### Decisive source
```python
previously_seen_type_refs = _generic_recursion_cache.get()
if previously_seen_type_refs is None:
    previously_seen_type_refs = set()
    token = _generic_recursion_cache.set(previously_seen_type_refs)
else:
    token = None
try:
    type_ref = _type_refs.model_type_ref(origin, args_override=args)
    if type_ref in previously_seen_type_refs:
        self_type = PydanticRecursiveRef(type_ref=type_ref)
        yield self_type            # second sighting → hand back a placeholder, DON'T recurse
    else:
        previously_seen_type_refs.add(type_ref)
        yield                      # first sighting → caller builds for real
        previously_seen_type_refs.remove(type_ref)
finally:
    if token:                      # only the OUTERMOST user resets the ContextVar
        _generic_recursion_cache.reset(token)
```

**Flow:** outermost caller allocates the seen-set and installs it in the ContextVar (keeps token); each nesting level computes its deterministic `type_ref`; repeat sighting ⇒ yield `PydanticRecursiveRef` (schema-level forward reference) so generation terminates; normal exit removes the ref so sibling fields can recurse again. `recursively_defined_type_refs()` exposes the CURRENT set so the schema generator can register definitions for refs that will exist.
**Invariant:** add-before-yield / remove-after-yield pairing is what makes re-entrant siblings work — porters who leak the ref break later independent uses of the same generic. Token reset ONLY by the allocator (token None ⇒ don't reset someone else's set).
**Probe:** `grep -n 'previously_seen_type_refs.remove' pydantic/_internal/_generics.py` (single :436 site pins the remove-after-yield discipline).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "generic recursion self type PydanticRecursiveRef", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the contextvar-scoped seen-set + recursive-ref placeholder pattern (works for ANY recursive builder, not just schemas); adapt `_type_refs.model_type_ref` naming to your identity scheme; omit the JSON-schema definition interplay.
