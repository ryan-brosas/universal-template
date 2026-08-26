<!-- capsule-v2 -->
# Two-stage generic type cache — why do early and late cache keys BOTH exist, and what makes `Model[List[T]][int] == Model[List[int]]`?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** What are the exact key shapes of the two lookups, and why is a WeakValueDictionary (plus a commented-out LimitedDict chain) used?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_generics.py:get_cached_generic_type_early` (:464-481), `_early_cache_key` (:532-541), `_late_cache_key` (:544-553), `set_cached_generic_type` (:494-508).
**Signature:** `_early_cache_key(cls, typevar_values) -> GenericTypesCacheKey` = `(cls, typevar_values, _union_orderings_key(typevar_values))`; `_late_cache_key(origin, args, typevar_values)` = `(union_orderings, origin, args)`.
**Data Shape:** `GenericTypesCacheKey = tuple[Any, Any, tuple[Any, ...]]`; store = `WeakValueDictionary` (`GenericTypesCache`); unhashable typevars are swallowed by `_generic_cache_get/_set` try/except TypeError.

### Decisive source
```python
def _late_cache_key(origin: type[BaseModel], args: tuple[Any, ...], typevar_values: Any) -> GenericTypesCacheKey:
    # The _union_orderings_key is placed at the start here to ensure there cannot be a collision with an
    # _early_cache_key, as that function will always produce a BaseModel subclass as the first item in the key,
    # whereas this function will always produce a tuple as the first item in the key.
    return _union_orderings_key(typevar_values), origin, args

def set_cached_generic_type(parent, typevar_values, type_, origin=None, args=None) -> None:
    _generic_cache_set(_early_cache_key(parent, typevar_values), type_)
    if len(typevar_values) == 1:
        # Cache bare parametrizations like Model[int] under the same entry as Model[int] used generically:
        _generic_cache_set(_early_cache_key(parent, typevar_values[0]), type_)
    if origin and args:
        _generic_cache_set(_late_cache_key(origin, args, typevar_values), type_)
```

**Flow:** `__class_getitem__` checks EARLY key first (cheap: class + raw typevars + union-ordering discriminator). On miss it proceeds to build; before building checks LATE key (expensive but exact: resolved origin+args) — a hit back-fills the early key via `set_cached_generic_type`. Union-orderings key exists because typing dedupes `Union[int, float]` vs `Union[float, int]`, so ordering must be carried OUT of band to keep distinct parametrizations distinguishable.
**Invariant:** Early-key-first is a performance contract for hot loops; late-key equivalence is the CORRECTNESS contract ("types that will ultimately be the same after resolving the type arguments will always produce cache hits"). Single-typevar values get an extra unwrapped-tuple early entry. WeakValueDictionary lets unreferenced dynamic classes be GC'd; the chained `LimitedDict(100)` fallback (commented out at :93) existed to keep recursive generics alive briefly — removing the weak layer breaks recursive generic construction.
**Probe:** `grep -n '_late_cache_key(origin, args, typevar_values)' pydantic/_internal/_generics.py` (:488 lookup + :508 back-fill pair).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "two stage generic cache early late key", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-key design + union-ordering discriminator + tuple-vs-class first-element collision guard; adapt cache size policy to your GC tolerance (re-read the LimitedDict comment before "simplifying"); omit py<3.9 alias translation branches.
