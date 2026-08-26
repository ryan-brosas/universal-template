<!-- capsule-v2 -->
# Query engine API surface — how do external callers run searches over parquet outputs, and why is every streaming variant a sync def returning an AsyncGenerator?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory `graphrag`. **Question:** what is the public query entry-point contract (DataFrame inputs, context capture via callback mutation, streaming-vs-collected pairing) across all four modes?

## api/query.py paired functions
**Path/Symbol:** `packages/graphrag/graphrag/api/query.py` (`global_search` :62-123, `global_search_streaming` :126-187, `local_search` :190-255, `local_search_streaming` :258-318, `drift_search` :321-383, `drift_search_streaming` :386-450, `basic_search` :453-501+, `basic_search_streaming` tail).
**Signature:** collected: `async def X(...) -> tuple[response, context_data]`; streaming: `def X_streaming(...) -> AsyncGenerator` — NOT async defs (they return the generator synchronously).
**Data Shape:** inputs are RAW pandas DataFrames (entities/communities/community_reports/text_units/relationships/covariates) + `community_level: int | None`; response accumulates string chunks; context_data captured via closure.

### Decisive source
```python
# api/query.py:101-107 — context capture hijacks a Noop callbacks object:
# the on_context ATTRIBUTE is replaced per-call so the engine's callback
# fan-out writes into this function's nonlocal frame; porters who pass
# plain dicts or await anything here miss that it's push-based
local_callbacks = NoopQueryCallbacks()
local_callbacks.on_context = on_context   # monkey-assigned
callbacks.append(local_callbacks)
```
```python
# :110-121 / :240-253 — collected variant IS the streaming variant consumed
# to completion (full_response += chunk); there is no separate execution
# path to keep in sync
async for chunk in global_search_streaming(...):
    full_response += chunk
```

**Flow:** validate_call type-gates → init_loggers(query.log) → adapters convert DataFrames (see indexer-adapters capsule) → `load_search_prompt` resolves prompt paths from config → `get_*_search_engine(config, ...)` builds engine with per-mode model ids (`config.local_search.completion_model_id` etc.) → return `search_engine.stream_search(query)`. DRIFT uniquely resolves TWO stores: entity-description + community-full-content embeddings (:421-429) and calls `read_indexer_report_embeddings` before engine construction.
**Invariant:** `callbacks.append(local_callbacks)` MUTATES the caller's list — callers passing their own callbacks list get the Noop appended permanently; redact() wraps vector-store config dumps before logging (:293). The four collected functions exist only as accumulate-and-return wrappers; any new mode must ship BOTH halves of the pair.
**Probe:** no dedicated unit file for api/query (CLI-level integration surface); pinned @pin by greps: `grep -c 'return search_engine.stream_search' api/query.py` = 4, `grep -c '@validate_call' api/query.py` = 8, `grep -c 'callbacks.append(local_callbacks)' api/query.py` = 4. Recorded caveat: verified by direct read; exercised upstream via CLI smoke.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "global search engine factory config response type", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved rank#1 `query.factory.get_global_search_engine` :103-180.

## Verdict
Adopt the paired collected/streaming shape, sync-def-returns-generator convention, and callback-attribute context capture; adapt DataFrame boundary to your storage layer; omit the pandas dependency by accepting your native row objects if adapters are ported alongside.
