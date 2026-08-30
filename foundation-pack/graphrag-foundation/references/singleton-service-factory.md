<!-- capsule-v2 -->
# Singleton service factory — how do you get DI-container semantics (transient vs arg-keyed singletons) in 113 lines with no framework?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory `graphrag`. **Question:** how does the shared Factory ABC cache singleton instances and why is the cache key a hash instead of the strategy name?

## Factory[T] ABC with ClassVar singleton
**Path/Symbol:** `packages/graphrag-common/graphrag_common/factory/factory.py` (`Factory.__new__` :31-35, `register` :51-71, `create` :73-113, `_ServiceDescriptor` :18-24) + `hasher.py` (`hash_data` :37-59).
**Signature:** `register(strategy: str, initializer: Callable[..., T], scope: ServiceScope = "transient")`; `create(strategy: str, init_args: dict | None = None) -> T`.
**Data Shape:** `_service_initializers: dict[str, _ServiceDescriptor[scope, initializer]]`, `_initialized_services: dict[hash_str, T]`.

### Decisive source
```python
# factory.py:96-111 — None-valued init args are STRIPPED (in Factory.create,
# BEFORE hashing) so {a:1, b:None} and {a:1} hit the SAME singleton;
# cache key = hash(strategy + sanitized args), NOT strategy alone —
# different configs coexist as distinct singletons
init_args = {k: v for k, v in (init_args or {}).items() if v is not None}
service_descriptor = self._service_initializers[strategy]
if service_descriptor.scope == "singleton":
    cache_key = hash_data({"strategy": strategy, "init_args": init_args})
    if cache_key not in self._initialized_services:
        self._initialized_services[cache_key] = service_descriptor.initializer(**init_args)
    return self._initialized_services[cache_key]
return service_descriptor.initializer(**(init_args or {}))
```
```python
# factory.py:29-35 — __new__ makes EACH SUBCLASS a per-class singleton via
# the inherited ClassVar; __init__ guards with hasattr(self, "_initialized")
# because __new__-returned instances re-run __init__ on every Factory()
_instance: ClassVar["Factory | None"] = None
def __new__(cls, *args, **kwargs):
    if cls._instance is None:
        cls._instance = super().__new__(cls, *args, **kwargs)
    return cls._instance
```

**Flow:** module import creates the singleton instance (`vector_store_factory = VectorStoreFactory()` at import time) → built-ins registered LAZILY on first create (`if strategy not in vector_store_factory:` match-arm imports the concrete class — heavy deps like lancedb never load unless selected) → unknown strategy raises ValueError listing REGISTERED strategies → create dispatches transient (fresh every call) or hash-cached singleton.
**Invariant:** hash stability depends on `yaml.dump(sort_keys=True)` with a fallback that converts sets/dicts/tuples into sorted tuples of strings (`make_yaml_serializable`) BEFORE dumping — port to JSON dumps without sort_keys and `{a:1,b:2}` vs `{b:2,a:1}` become two different singletons for identical config. The None-stripping happens in `create` BEFORE the hash is taken (hash_data itself would happily serialize `b: null`); a porter who moves stripping after hashing breaks default-arg singleton equivalence. Lazy registration means `keys()` can be empty-looking early; membership check must use `strategy not in factory` not keys-list inspection.
**Probe:** `tests/unit/graphrag_factory/test_factory.py` — one test pins BOTH scopes: trans1 is not trans2, single1 IS single2 (:44-67). Executed @pin: `/home/utopia/.venvs/grag-lane-venv/bin/python -m pytest tests/unit/graphrag_factory/ -q` → 1 passed. Post-commit behavioral battery additionally proved None-stripped equivalence through the real Factory path with a minimal VectorStore subclass: `create("vs", {index_name:"x", vector_size:None}) IS create("vs", {index_name:"x"})` → True.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "Factory singleton transient strategy register create", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved rank hits incl. `factory.Factory.register` :51-71 + four integration test_register_and_create_custom_* twins.

## Verdict
Adopt the descriptor+scope model, None-stripping before hashing, lazy match-import registration, and loud unknown-strategy error listing alternatives; adapt hashing to host's canonical serializer (keep it ORDER-STABLE); omit the covariant TypeVar ceremony if not typing backends. No coverage caveat.
