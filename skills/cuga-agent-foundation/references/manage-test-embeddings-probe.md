<!-- capsule-v2 -->
# Embedding test-connection probe — how do you validate embedding credentials BEFORE save with a throwaway engine, and what does each error_class mean?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How does `POST /knowledge/test_embeddings` fail fast (validation vs connectivity vs timeout) while guaranteeing no temp-dir leak, and why reuse the live factory?

## Throwaway KnowledgeConfig in a temp dir + to_thread + 10s wait_for + rmtree in outer finally
**Path/Symbol:** `src/cuga/backend/server/manage_routes/knowledge_routes.py:25-108` (`test_embeddings_connection`).
**Signature:** body `{provider, model, api_key, base_url, extra_params}` → `{ok: true, dim: int, latency_ms: int}` or `{ok: false, error_class: "InvalidEmbeddingConfiguration" | "EmbeddingConnectionFailed" | "Timeout", error: str}`.
**Data Shape:** dim = `len(embed_query("connection test"))` — the measured dimension, not a declared one; latency = monotonic-clock ms around factory+embed.

### Decisive source
```python
# knowledge_routes.py:53-57, 95-108
# Build a throwaway config; reuse the same factory the live engine uses so
# the test path matches reality. The temp dir is removed in the outer
# finally so a Test Connection call (incl. validation failures / timeouts)
# doesn't leak a directory each time.
tmp_dir = Path(tempfile.mkdtemp(prefix="cuga-test-emb-"))
...
result = await _asyncio.wait_for(_asyncio.to_thread(_do_test), timeout=10.0)
...
except _asyncio.TimeoutError:
    return JSONResponse({"ok": False, "error_class": "Timeout", ...})
finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)
```
Three failure tiers are deliberately distinct: config validation errors (ValueError/TypeError from `KnowledgeConfig.validate`) → `InvalidEmbeddingConfiguration` without touching the network; any exception inside factory/embed → generic `EmbeddingConnectionFailed` (provider detail logged only); wall-clock >10s → `Timeout` with "check base URL reachable / model correct". The docstring states the product rationale: surface failures BEFORE save rather than 30s into an ingest.

**Flow:** parse+strip body → require provider (400 if absent) → mkdtemp → construct KnowledgeConfig(persist_dir=tmp_dir, enabled=True, ...) → `.validate()` → thread-offloaded `_do_test` (create_embeddings(cfg) → embed_query) under `wait_for(10s)` → classify result/timeout → outer finally removes tmp dir on EVERY path.
**Invariant:** The probe must exercise the SAME `create_embeddings` factory as the live engine (a passing fake would be worthless), must never raise into HTTP (all failures are structured `{ok:false}` responses), and must not leak its scratch dir even on validation failure or timeout. The sync embed call is off-loop via `to_thread` so the probe can't stall the server it's testing against.

**Probe:** No direct unit test at HEAD (coverage caveat) — source-read verified; the same factory contract's failure taxonomy is pinned by `tests/unit/test_knowledge_embedder_load_error.py` and `tests/unit/test_knowledge_litellm.py::test_create_embeddings_*` (:173/:185).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "test_embeddings_connection create_embeddings embed_query connection test", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-tier error classification + throwaway-engine-under-timeout pattern for any pre-save credential check. Adapt the config type. Omit latency_ms if you don't render it. Coverage caveat recorded: no direct route test at HEAD.
