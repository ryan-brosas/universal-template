<!-- capsule-v2 -->
# Two-layer LM cache — why does an LRU sit in FRONT of a disk cache, and what does each layer buy you?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** How do you combine an in-process LRU with litellm's disk cache so identical prompts are free across turns AND across runs?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/lm.py:cached_litellm_completion` (:115-122) + module-global cache wiring (:29-43).
**Signature:** `@functools.lru_cache(maxsize=3000) def cached_litellm_completion(request: str) -> response`; `request = ujson.dumps(dict(model=..., messages=..., **kwargs))`.
**Data Shape:** The cache key is the full request JSON string (model + messages + sampling kwargs). `cache=False` per call bypasses BOTH layers; `cache=True` routes through the LRU which forwards with `cache={"no-cache": False, "no-store": False}` enabling the litellm disk layer.

### Decisive source
```python
LM_LRU_CACHE_MAX_SIZE = 3000
# module import time:
os.environ.setdefault-equivalent:  if "LITELLM_LOCAL_MODEL_COST_MAP" not in os.environ:
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"   # avoid remote cost-map fetch
litellm.drop_params = True    # silently drop provider-unsupported params
litellm.telemetry = False
litellm.cache = Cache(disk_cache_dir=os.path.join(Path.home(), ".storm_local_cache"), type="disk")

@functools.lru_cache(maxsize=LM_LRU_CACHE_MAX_SIZE)
def cached_litellm_completion(request):
    return litellm_completion(request, cache={"no-cache": False, "no-store": False})
def litellm_completion(request, cache={"no-cache": True, "no-store": True}):
    kwargs = ujson.loads(request)
    return litellm.completion(cache=cache, **kwargs)
```

**Flow:** `__call__` serializes the whole call to one JSON string → picks cached vs uncached fn by the instance `cache` flag → LRU hit returns instantly; miss → litellm completion consults the process-global disk cache (`~/.storm_local_cache`) → network only on double-miss. The same pair exists for text completions (:125-155).
**Invariant:** (1) Keying on the serialized request makes the cache sensitive to EVERY kwarg — two calls differing only in temperature never collide. (2) The LRU and disk layers must agree on bypass semantics: uncached path passes `no-store: True`. (3) `drop_params=True` is global — porters who need strict param validation must flip it deliberately. (4) History entries record `cost=None` shape from `_hidden_params.response_cost`, so cache hits show as free.
**Probe:** deterministic pin — lm.py:32-43 excerpt byte-verified this pass (probe PIN litellm env-default + disk cache GREEN); lifted probe harness at `.pi/work/foundations-deep-farm/scratch-storm-pass1/probe_gate5.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "cached_litellm_completion lru cache disk", limit: 10 });
```

## Verdict
Adopt the layered scheme verbatim for any multi-turn research agent: LRU kills repeat latency inside a run, disk cache kills cost across runs; adapt the cache dir/env names; omit the o1- assert twin (`"o1-" in model → temperature==1.0 & max_tokens>=5000`, :73-76) unless serving OpenAI reasoning models. Caveat: no upstream tests; source-pinned.
