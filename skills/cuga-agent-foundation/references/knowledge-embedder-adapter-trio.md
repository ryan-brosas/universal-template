<!-- capsule-v2 -->
# Embedder adapter trio — what does each local/cloud embedding backend hide (E5 prefixes, cache self-heal, MPS pooling, LiteLLM ordering), and which invariants do callers silently depend on?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When porting the LangChain `Embeddings` implementations, which per-backend behaviors are load-bearing rather than incidental?

## _FastEmbedEmbeddings / _PyTorchEmbeddings / _LiteLLMEmbeddings — one adapter per transport
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py:909-1014` (`_FastEmbedEmbeddings` + `_purge_model_cache` :902-906), `:1017-1092` (`_PyTorchEmbeddings`), `:1115-1205` (`_LiteLLMEmbeddings`).
**Signature:** all implement `embed_documents(texts) -> list[list[float]]` / `embed_query(text) -> list[float]`.
**Data Shape:** fastembed: ONNX session providers probed by attribute walk (`model/_model/session/ort_session`, 4 levels); CUDA ⇒ embed kwargs `{batch_size:256, parallel:1}`; E5 detection `"e5" in name and ("intfloat" or "multilingual" or startswith("e5"))` ⇒ prefixes `query: `/`passage: `. PyTorch: mean-pool over attention mask → L2 normalize; `_max_seq_len = model_max_length or 512`, sentinel >8192 clamped to 512; internal BATCH=32. LiteLLM: reserved-kwargs filter `{model,input,api_key,api_base,allow_insecure_transport}`.

### Decisive source
```python
# engine.py:934-952 (fastembed self-heal) and :1187-1198 (litellm reorder)
# A purged or interrupted download leaves a dangling snapshot
# symlink ... onnxruntime hard-fails with NoSuchFile on EVERY
# subsequent start -- the user is bricked ...
if local_files_only or cache_root is None or not _is_corrupt_model_cache_error(exc):
    raise
... _purge_model_cache(cache_root)
# Exactly once. A second failure is a genuine fault ... must surface.
...
# LiteLLM does NOT guarantee returned order matches input order -- sort by index.
ordered = sorted(data, key=lambda d: int(d.get("index", 0) ...))
...
raise RuntimeError(f"litellm returned {len(out)} vectors for {len(texts)} inputs")
```
LiteLLM base_url guard (:1149-1164): http allowed ONLY for loopback hosts unless `extra_params.allow_insecure_transport=true` — remote plaintext HTTP is a config error, not a warning. PyTorch exists for GPU locality (MPS ~8× fastembed-CPU on M-series) using deps Docling already ships; tensors are moved to CPU before `.tolist()` because MPS tensors need explicit transfer (:1079).

**Flow (fastembed):** TextEmbedding(...) → on failure classify corrupt-cache (`_is_corrupt_model_cache_error`) vs genuine fault → purge that ONE hashed cache entry + sibling HF lock dir → retry exactly once → detect active ORT providers → pick GPU/CPU embed kwargs → set E5 prefixes. **Flow (query):** prefix injection happens per call; documents get passage:, queries get query:. **Flow (litellm):** lazy `import litellm.embedding` per call → kwargs merge → response.data sorted by index → count mismatch raises RuntimeError.
**Invariant:** Embedding adapters own correctness details callers never see: E5 without prefixes loses 3-5 MRR points; out-of-order LiteLLM responses would silently misalign vectors to texts if not re-sorted (count mismatch must raise, not truncate); corrupt-cache healing retries EXACTLY once so offline/disk-full surfaces instead of looping; batch shape is a performance contract only on CUDA (CPU defaults untouched).

**Probe:** `tests/unit/test_embedder_cache_resilience.py` — corrupt-classification :34-42, purge+lock removal :90, self-heal reload :147, exactly-once :161, non-corruption no-retry :174; `tests/unit/test_knowledge_litellm.py` — input-order restore :74/:87, size-mismatch raise :102, http-base-url ladder :109/:120/:129/:140.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_FastEmbedEmbeddings _LiteLLMEmbeddings _PyTorchEmbeddings _purge_model_cache", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: index-sorted litellm responses + count assertion, once-only cache self-heal, E5 prefix injection, attention-mask mean-pool + L2 norm. Adapt provider probing to your runtime versions. Omit the PyTorch adapter if you have no local-GPU story. Direct tests pin both cloud/local contracts.
