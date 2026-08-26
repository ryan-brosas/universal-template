<!-- capsule-v2 -->
# Index persistence layout — the save/load directory contract and pickle-fallback config format

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** What must an index directory contain, in what format does config persist, and how do legacy indexes keep loading?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/embeddings/base.py:Embeddings.save` (:606-662), `.load` (:533-604), `.exists` (:507-531); `embeddings/index/configuration.py:Configuration.load/.save`; archive check `.checkarchive` (:922-941).
**Signature:** `save(path, cloud=None)` / `load(path)`; path may be a tar.gz/zip (routed through ArchiveFactory).
**Data Shape:** fixed subpaths: `config.json|config`, `embeddings`, `lsa`, `ids`, `documents`, `scoring`, `indexes/<name>`, `graph`.

### Decisive source
```python
# Configuration.load — json default, pickle fallback for legacy
jsonconfig = os.path.exists(f"{path}/config.json")
name = "config.json" if jsonconfig else "config"
with open(f"{path}/{name}", "r" if jsonconfig else "rb", encoding="utf-8" if jsonconfig else None) as handle:
    config = json.load(handle) if jsonconfig else SerializeFactory.create("pickle").loadstream(handle)
config["format"] = "json" if jsonconfig else "pickle"
```
```python
# exists() requires the offset marker — distinguishes a complete index from a partial save
return path and (os.path.exists(f"{path}/config.json") or os.path.exists(f"{path}/config")) and "offset" in Configuration().load(path)
```

**Flow (load):** cloud fetch → archive extract → config load (+ overrides merge) → per-component create+load IN FIXED ORDER: ann(embeddings/) → reducer(lsa/) → ids(ids/) → database(documents/) → scoring(scoring/) → subindexes(indexes/<name>/, skipped when absent — subindexes aren't required to have data) → graph(graph/) → vectors model → query model.

**Invariant:** `offset` in config is the completeness marker (`exists()` fails without it); each component's load is conditional on its factory producing an instance from config — a porter must not eagerly open files for disabled components. Config round-trips through JSON with `default=str` (non-JSON values stringify), and `format` key records which loader produced it. Subindex directories are optional at load but always created at save.

**Probe:** `test/python/testembeddings.py:testSave` (:450-472), `testIdsPickle` (:289-314 legacy ids-in-config format), `testarchive.py` (compressed index files).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "Configuration save load offset archive format", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt directory layout + offset completeness marker + dual-format config loading + optional-subindex loads; adapt formats to your serializer; omit cloud/archive layers when local-only.
