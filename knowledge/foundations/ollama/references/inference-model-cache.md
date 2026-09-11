<!-- capsule-v2 -->
# Inference model cache — how is per-request model resolution made cheap without serving stale metadata?

**Source:** Ollama MIT `main@fb30760996871fa9460115c753afd2c60d4ab0f7`; Codebase Memory `ext-ollama`. **Question:** How do you cache fully-resolved models (capabilities included) so concurrent requests don't stampede and re-pulled models never serve stale data?

## inferenceModelCache (digest-validated + singleflight + deep clone)
**Path/Symbol:** `server/model_inference_cache.go` (struct :18-28, `Get` :41-84, `cloneInferenceModel` :86-114, `getModel` shim :116-121). **Signature:** `func (c *inferenceModelCache) Get(name string) (*Model, error)`.
**Data Shape:** Key = `{name, goTemplate, goTemplateSet}` — the Go-template ENV decision changes derived capabilities, so it is part of identity. Entry = `{digest string, model *Model}`. Loads deduped by singleflight key `name\x00digest\x00goTemplate\x00goTemplateSet`.

### Decisive source
```go
mf, err := manifest.ParseNamedManifest(n)   // digest = freshness boundary
digest := mf.Digest()
c.mu.RLock(); entry, ok := c.entries[key]; c.mu.RUnlock()
if ok && entry.digest == digest { return cloneInferenceModel(entry.model), nil }
v, err, _ := c.loads.Do(loadKey, func() (any, error) {
    // double-check inside the flight — another goroutine may have loaded already
    ...
    m, err := c.loadModel(name)
    m.capabilities = m.Capabilities()   // precompute; Capabilities() later hits cache
    m.capabilitiesCached = true
    c.entries[key] = inferenceModelCacheEntry{digest: m.Digest, model: m}
    return m, nil
})
return cloneInferenceModel(v.(*Model)), nil  // EVERY caller gets a private copy
```
```go
// clone list is explicit: slices.Clone on ModelFamilies/Capabilities/AdapterPaths/
// ProjectorPaths/License/Messages/capabilities, maps.Clone on Options, value-copy of *Config.Draft.
```

**Flow:** Every inference request resolves its model through this cache (Server.getModel falls back to raw GetModel only when caches are nil). Manifest digest re-read per call makes staleness impossible: a re-pull changes the digest ⇒ miss ⇒ reload. Singleflight collapses N concurrent misses for the same (model,digest,env) into one disk load. Because handlers mutate request-scoped fields (`req.Think`, parser name patching like `m.Config.Parser = "harmony"`), every returned model must be a deep clone — hence the enumerated clone function rather than reflect-based copying, keeping unexported capability fields intact.
**Invariant:** Cache hit REQUIRES matching live digest, not just key presence; no shared mutable Model escapes the cache; capability precomputation happens exactly once inside the flight.
**Probe:** `grep -cF "entry.digest == digest" server/model_inference_cache.go` → `2` (outer check + in-flight double-check); `grep -cF "cloneInferenceModel(entry.model)" server/model_inference_cache.go` → `1`. Direct tests: `server/model_inference_cache_test.go` `TestInferenceModelCache`, `TestInferenceModelCacheConcurrentMiss` (PASS at pin via `go test ./server/ -run TestInferenceModelCache`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ollama", query: "cloneInferenceModel getModel caches entries", limit: 5 });
```

## Verdict
Adopt digest-validation + singleflight + hand-written deep clone as one unit. Adapt the freshness oracle (any content-addressed manifest works); omit show/list cache siblings unless porting the whole /api surface.
