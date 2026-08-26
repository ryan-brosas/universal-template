<!-- capsule-v2 -->
# ANN factory + setting resolution — backend table, custom backends, and the falsy-but-present settings trap

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** How are ANN backends resolved from config (including dotted custom classes) and how must per-backend settings be read?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/ann/dense/factory.py:ANNFactory.create/.resolve` (:20-77); `src/python/txtai/ann/base.py:ANN.setting` (:112-129), `.metadata` (:131-153).
**Signature:** `ANNFactory.create(config)` → ANN instance; `setting(name, default=None)`.
**Data Shape:** `config["backend"]` = name or dotted class; per-backend dict keyed by backend name (`config["faiss"]["nprobe"]`); build metadata under `config["build"]`.

### Decisive source
```python
backend = config.get("backend", "faiss" if FAISS else "numpy")
...
else:
    ann = ANNFactory.resolve(backend, config)

# Store config back
config["backend"] = backend

# base.ANN.setting — the load-bearing line:
return setting if setting or (backend and name in backend) else default
```
```python
# metadata(): ISO-8601 UTC stamp, python/txtai versions, system arch, build settings on NEW builds only
if settings:
    self.config["build"] = {"create": create, "python": platform.python_version(), "settings": settings, "system": f"{platform.system()} ({platform.machine()})", "txtai": __version__}
self.config["update"] = create
```

**Flow:** backend name → builtin table (annoy/faiss/hnsw/milvus/ggml/numpy/pgvector/sqlite/torch/turbovec/zvec) else `Resolver()` dotted-path import wrapped as ImportError("Unable to resolve ann backend") → resolved backend name WRITTEN BACK into config so save/load round-trips the same backend → every backend reads its knobs through `ANN.setting`, which looks up `config[config["backend"]][name]`.

**Invariant:** `setting()` distinguishes None-from-absent via `name in backend`: a setting explicitly set to 0/False must return 0/False, not the default — a porter using `dict.get(name, default)` breaks nprobe=0-style overrides and boolean-off flags. Default backend is faiss when importable else numpy — availability-dependent defaults must be recorded, not recomputed at load. `metadata()` sets "build" once and refreshes "update" on every append.

**Probe:** `test/python/testann/testdense.py:testCustomBackend/testCustomBackendInvalid/testCustomBackendNotFound` (:43-64), `testNotImplemented` (:218+), backend matrix tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "ANNFactory resolve setting backend Resolver", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the factory table + write-back + presence-aware setting lookup + build/update metadata split; adapt backend names; omit Resolver if you disallow custom backends.
