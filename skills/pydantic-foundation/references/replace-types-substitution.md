<!-- capsule-v2 -->
# `replace_types` typevar substitution — how are type args rewritten recursively without rebuilding unchanged types?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** What is the recursion contract of `replace_types`, and which special forms need dedicated handling?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_generics.py:replace_types` (:257-351).
**Signature:** `def replace_types(type_: Any, type_map: Mapping[TypeVar, Any] | None) -> Any`.
**Data Shape:** Identity fast path when `type_map` empty; returns SAME object when nothing changed (`all_identical` guard), new alias otherwise.

### Decisive source
```python
if not type_map:
    return type_
type_args = get_args(type_)
origin_type = get_origin(type_)

if typing_objects.is_annotated(origin_type):
    annotated_type, *annotations = type_args
    annotated_type = replace_types(annotated_type, type_map)
    return Annotated[(annotated_type, *annotations)]   # annotations NOT substituted

if type_args:
    resolved_type_args = tuple(replace_types(arg, type_map) for arg in type_args)
    if all_identical(type_args, resolved_type_args):
        return type_                                    # no change → same object
    if is_union_origin(origin_type):
        if any(typing_objects.is_any(arg) for arg in resolved_type_args):
            resolved_type_args = (Any,)                 # `Any | T` ~ `Any`
        resolved_type_args = tuple(arg for arg in resolved_type_args
                                   if not (typing_objects.is_noreturn(arg) or typing_objects.is_never(arg)))
    if sys.version_info < (3, 14) and origin_type is types.UnionType:
        return reduce(operator.or_, resolved_type_args)  # PEP-604 unions lack __getitem__
    return origin_type[resolved_type_args[0] if len(resolved_type_args) == 1 else resolved_type_args]

# pydantic generic MODELS: parametrize via __getitem__ on the class itself
if not origin_type and is_model_class(type_):
    parameters = type_.__pydantic_generic_metadata__['parameters']
    ...
    return type_[resolved_type_args]
...
return type_map.get(type_, type_)   # leaf: substitute or keep
```

**Flow:** recurse into args; collapse identity results to preserve object identity (critical for cache keys); normalize unions (Any absorbs, Never/NoReturn drop); rebuild via `origin[...]`, `reduce(or_)` for PEP-604 (pre-3.14), or model `__getitem__`; handle list-args Callable form; finally map bare leaves.
**Invariant:** `get_args`/`get_origin` here are PYDANTIC-AWARE — they read `__pydantic_generic_metadata__` before falling back to typing_extensions, so generic models participate in substitution. Annotations on `Annotated[...]` are intentionally left untouched.
**Probe:** `grep -n 'def replace_types' pydantic/_internal/_generics.py` (:257) + doctest inside the docstring pins `replace_types(tuple[str, list[str] | float], {str: int}) == tuple[int, list[int] | float]`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "replace_types typevar map recursive", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the identity-preserving recursion and union normalization; adapt the model-metadata branch to your own generic representation; omit <3.14 UnionType translation comments.
