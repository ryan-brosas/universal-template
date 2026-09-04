<!-- capsule-v2 -->
# WrapperCapability — transparent capability wrapper with identity adoption

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a porter wraps one capability in another (to override a few hooks), how does the wrapper stay transparent — adopting the wrapped capability's id/defer_loading and delegating everything else — without re-running `__init__` on rebind?

## WrapperCapability delegation + identity adoption
**Path/Symbol:** `pydantic_ai/capabilities/wrapper.py:WrapperCapability` (48-480).
**Signature:** `WrapperCapability(wrapped: AbstractCapability)`; delegates every method to `self.wrapped`.
**Data Shape:** `wrapped` is the inner capability. `__post_init__` runs `__adopt_wrapped_identity`.

### Decisive source
```python
def __post_init__(self):
    self.__adopt_wrapped_identity()

def __adopt_wrapped_identity(self):
    # A wrapper is transparent by default: with no explicit `id` of its own, it adopts
    # the wrapped capability's `id` and `defer_loading`.
    if self.id is None:
        self.id = self.wrapped.id
        self.defer_loading = self.wrapped.defer_loading

def for_agent(self, agent):
    new_wrapped = self.wrapped.for_agent(agent)
    if new_wrapped is self.wrapped:
        return self
    new_self = replace_no_init(self, wrapped=new_wrapped)   # shallow copy, NO __init__ re-run
    new_self.__adopt_wrapped_identity()
    return new_self
```

**Flow:** `WrapperCapability` delegates every hook/get method to `self.wrapped`. On construction (and on every rebind from `for_agent`/`for_run`), `__adopt_wrapped_identity` copies the wrapped capability's `id` and `defer_loading` onto the wrapper — but only if the wrapper has no explicit `id` of its own. Rebinds use `replace_no_init` (shallow copy, `__init__`/`__post_init__` NOT re-run), then re-adopt identity so it re-resolves against the NEW wrapped instance (e.g. one a `DynamicCapability` produced at run time, whose id only becomes known after the factory runs).
**Invariant:** A wrapper over a deferred capability keeps its deferral and its place in the load catalog (identity adoption). Rebinds preserve subclass state verbatim (no `__init__` re-run) but MUST re-run identity adoption. `apply` registers the wrapper itself plus, if the wrapped is a container, its leaves (so child-owned hooks/toolsets resolve their capability ids).
**Probe:** `tests/test_capabilities.py` covers wrapper-capability identity adoption and delegation (wrapper-over-deferred-capability load-gating tests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "WrapperCapability __adopt_wrapped_identity replace_no_init", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the transparent-delegation + identity-adoption-on-rebind pattern (with `replace_no_init` shallow copy); adapt the id/defer_loading fields to your host; omit nothing — the no-`__init__`-re-run + re-adopt-identity pairing is the portable invariant. Coverage clean.
