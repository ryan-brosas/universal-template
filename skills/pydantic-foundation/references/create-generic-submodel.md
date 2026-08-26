<!-- capsule-v2 -->
# Dynamic parametrization via `create_generic_submodel` — how is the concrete subclass minted, pickled, and kept weakref-able?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** When `Model[int]` runs, what namespace does the metaclass receive and what global-name bookkeeping makes pickle work?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_generics.py:create_generic_submodel` (:104-161).
**Signature:** `def create_generic_submodel(model_name: str, origin: type[BaseModel], args: tuple[Any, ...], params: tuple[Any, ...]) -> type[BaseModel]`.
**Data Shape:** Injects `__pydantic_generic_metadata__={'origin', 'args', 'parameters'}` as metaclass kwargs; sets `__pydantic_reset_parent_namespace__=False`.

### Decisive source
```python
namespace: dict[str, Any] = {'__module__': origin.__module__}
# forward __slots__ from the origin so dynamic subclasses stay weakref-able / match parent layout:
if '__slots__' in origin.__dict__:
    namespace['__slots__'] = origin.__dict__['__slots__']
bases = (origin,)
meta, ns, kwds = prepare_class(model_name, bases)
namespace.update(ns)
created_model = meta(model_name, bases, namespace,
                     __pydantic_generic_metadata__={...}, __pydantic_reset_parent_namespace__=False, **kwds)

model_module, called_globally = _get_caller_frame_info(depth=3)
if called_globally:  # create global reference and therefore allow pickling
    object_by_reference = None
    reference_name = model_name
    reference_module_globals = sys.modules[model_module or created_model.__module__].__dict__
    while object_by_reference is not created_model:
        object_by_reference = reference_module_globals.setdefault(reference_name, created_model)
        reference_name += '_'
```

**Flow:** build minimal namespace (module + forwarded slots) → `types.prepare_class` resolves the metaclass and ITS `__prepare__` dict (`_ModelNamespaceDict`) → call metaclass with generic metadata and parent-namespace reset DISABLED (parametrizations must NOT capture the caller's frame for forward refs) → if invoked at module top level, register the class under its name (appending `_` until free) in the CALLER's module globals so `pickle` finds a qualified path.
**Invariant:** `prepare_class` (not direct `meta(...)`) is required so `__prepare__` supplies the warning-aware namespace dict. The global-registration loop MUST use `setdefault` (never clobber an existing binding) and only fires when called globally (`f_locals is f_globals`) — locals-created parametrizations stay anonymous by design.
**Probe:** `grep -n "reference_name += '_'" pydantic/_internal/_generics.py` (single :159 site pins the unique-name loop).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "create_generic_submodel prepare_class pickling global reference", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the metadata-through-metaclass-kwarg pattern, slots forwarding, and conditional global registration; adapt frame-depth magic (`depth=3`) to your call structure; omit typing-inspection dependency specifics.
