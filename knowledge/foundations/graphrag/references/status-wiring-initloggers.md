<!-- capsule-v2 -->
# Reporting-sink selection & status wiring — how does GraphRAG choose a reporting sink and point ONE handler at every package logger?

**Source:** graphrag (MIT) `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory project `graphrag`. **Question:** How do config-selected reporting sinks get registered, lazily imported, and attached across the `graphrag` and `graphrag_llm` namespaces without duplicate logs?

## LoggerFactory + init_loggers — registry selection over shared-handler wiring
**Path/Symbol:** `packages/graphrag/graphrag/logger/factory.py`: `LoggerFactory(Factory[logging.Handler])` (:19-29), `create_file_logger` (:33-46), `create_blob_logger` (:49-58), registrations (:63-64); `packages/graphrag/graphrag/logger/standard_logging.py`: `init_loggers` (:50-91); `packages/graphrag/graphrag/logger/progress.py`: `Progress`/`ProgressHandler`/`ProgressTicker` (:15-71).
**Signature:** `logger_factory.register(ReportingType.file.value, create_file_logger)` / `(ReportingType.blob.value, create_blob_logger)`; `init_loggers(config: GraphRagConfig, verbose: bool = False, filename: str = DEFAULT_LOG_FILENAME) -> None`; `ProgressTicker(callback: ProgressHandler | None, num_total: int, description: str = "")` invoked as `ticker(n_ticks=1)`.
**Data Shape:** factory args = `reporting.model_dump()` + `filename` override; handlers are plain `logging.Handler`s; progress events are a 3-field dataclass broadcast through a nullable callback.

### Decisive source
```python
# standard_logging.py — close-before-clear dup guard, then ONE handler, TWO namespaces
def _clear_handlers(logger):
    if logger.hasHandlers():
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.close()
        logger.handlers.clear()
_clear_handlers(logger); _clear_handlers(llm_logger)
handler = LoggerFactory().create(reporting_config.type, {**config_dict, "filename": filename})
logger.addHandler(handler); llm_logger.addHandler(handler)   # SAME instance on 'graphrag' + 'graphrag_llm'

# factory.py — Azure import deferred into the sink builder
def create_blob_logger(**kwargs) -> logging.Handler:
    from graphrag.logger.blob_workflow_logger import BlobWorkflowLogger
    return BlobWorkflowLogger(connection_string=kwargs["connection_string"], ...)
```

**Flow:** config `reporting.type` string → factory registry hit → builder kwargs enforced per-sink → handler attached to BOTH root loggers → every `logging.getLogger("graphrag.*")` / `graphrag_llm.*` record flows to one sink. Progress side-channel: `progress_iterable` ticks BEFORE yield (auto-`len()` when total omitted), ticker logs `"desc done/total"` then calls the callback; `.done()` forces completed=total.
**Invariant:** re-init must CLOSE existing FileHandlers before clearing (else duplicated logs and leaked file descriptors), and the two package roots share one handler instance so sink count stays 1 regardless of namespace count. File-only installs never import azure (lazy import lives inside the builder body).
**Probe:** `tests/integration/logging/test_standard_logging.py` — hierarchy propagation + file-config init. EXECUTED pre-write: `pytest tests/integration/logging/test_standard_logging.py` → **5 passed** (offline-capable: tempfile + explicit chdir).

## Get live surrounding code
**Retrieve:** (executed live; rank-line-exact)
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "init_loggers LoggerFactory ReportingType file blob handler", limit: 10 });
// rank#4 graphrag.packages.graphrag.graphrag.logger.standard_logging.init_loggers :50-91;
// integration test_init_loggers_* rows rank #2/#3/#5
```

## Verdict
Adopt registry-keyed sink selection with lazy heavy-import builders, the close-before-clear guard, and shared-handler multi-namespace attach. Adapt ReportingType keys, formats (`LOG_FORMAT` msecs style), and the Progress dataclass fields to host vocabulary. Omit Azure-only builder internals. Coverage caveat: blob sink behavior itself is pinned by the unit suite (see blob-workflow-logger capsule).
