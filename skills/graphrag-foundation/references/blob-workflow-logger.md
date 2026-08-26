<!-- capsule-v2 -->
# Blob append-log workflow sink — how do I stream workflow logs to durable object storage without corrupting the handler or blowing the block budget?

**Source:** graphrag (MIT) `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory project `graphrag`. **Question:** How does an indexing workflow persist per-run logs as structured JSON to blob storage while rotating safely under append-blob block limits?

## BlobWorkflowLogger — logging.Handler over an Azure append blob
**Path/Symbol:** `packages/graphrag/graphrag/logger/blob_workflow_logger.py`: `BlobWorkflowLogger` (:15-121); rotation core `_rotate_blob` (:91-104), writer `_write_log` (:107-121), funnel `emit` (:62-81).
**Signature:** `__init__(connection_string: str | None, container_name: str | None, blob_name: str = "", base_dir: str | None = None, account_url: str | None = None, level: int = logging.NOTSET)`; class const `_max_block_count: int = 25000`.
**Data Shape:** one JSON object per block: `{"type": "log"|"warning"|"error", "data": msg[, "details"][, "cause"][, "stack"]}` appended (indent=4, ensure_ascii=False, trailing newline) to an append blob named `report/{UTC %Y-%m-%d-%H:%M:%S:%f}.logs.json` nested under optional `base_dir`. Constructor ladder: container required (ValueError) → connection_string XOR account_url (`DefaultAzureCredential` fallback) → initial rotate creates the append blob if missing and zeroes `_num_blocks`.

### Decisive source
```python
# rotate BEFORE append; counter is the only rotation state
def _write_log(self, log: dict[str, Any]):
    if self._num_blocks >= self._max_block_count:
        self._rotate_blob()

    blob_client = self._blob_service_client.get_blob_client(self._container_name, self._blob_name)
    blob_client.append_block(
        (json.dumps(log, indent=4, ensure_ascii=False) + "\n").encode("utf-8")
    )
    self._num_blocks += 1

# levelno → wire type: ERROR+ → error, WARNING+ → warning, else log
except (OSError, ValueError):
    self.handleError(record)   # anything else propagates into logging
```

**Flow:** `emit(record)` → type-map by `record.levelno` → collect details/cause/stack when present → `_write_log` → rotate-if-full → `append_block` → counter++ . Rotation picks a fresh timestamped name, `create_append_blob()` when absent, resets counter — it never touches handler state.
**Invariant:** ROTATION MUST NOT RE-RUN `__init__`. A logging.Handler's lock is held by the logging framework during emit; re-initializing mid-flight replaced the lock and deadlocked releases (upstream issue #2170). New blob identity + client, same handler instance.
**Probe:** `tests/unit/logger/test_blob_workflow_logger.py` — 7 tests; `test_rotate_blob_does_not_reinitialize_handler` (:86-113) pins `logger.lock is original_lock` after a boundary write plus `_num_blocks == 1`. EXECUTED pre-write: `pytest tests/unit/logger tests/unit/load_config` → **13 passed** (lane venv, editable installs @pin).

## Get live surrounding code
**Retrieve:** (executed live; rank-line-exact)
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "BlobWorkflowLogger append blob rotation block count", limit: 10 });
// rank#3 packages/graphrag/graphrag/logger/blob_workflow_logger.BlobWorkflowLogger._rotate_blob :91-104;
// rank#4 __init__ :22-60; rank#5 emit :62-81; tests/unit/logger ranks #1/#2
```

## Verdict
Adopt the rotate-before-append counter discipline, the never-reinit-handler rule, and the three-level type map. Adapt blob naming/base_dir and credential choice to host storage. Omit Azure SDK specifics if the host sink differs — keep the JSONL frame `{type,data,...}` so consumers survive. Coverage caveat: none (direct unit suite exists and was executed).