<!-- capsule-v2 -->
# Knowledge engine single-writer flock — how do you guarantee one process owns the vector store, and how do you stop a cold embedder from being loaded twice?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What happens when a second process tries to start the knowledge engine, and why does lazy embedder init need its own thread lock?

## Construction-time exclusive flock + embedder init mutex
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py:1760-1767` (lock acquisition), `:1781-1790` (`_embedder_initializing` + `_embedder_init_lock`), `knowledge/interprocess_lock.py:8-33` (`acquire_exclusive_nonblocking`, `release_exclusive`).
**Signature:** `acquire_exclusive_nonblocking(lock_file: IO) -> None` (flock on Unix, msvcrt 1-byte LK_NBLCK on Windows); `KnowledgeEngine.__init__(config, chat_generator=None)`.
**Data Shape:** Lock lives at `<persist_dir>/.lock`, opened `w+b`, held for the ENGINE'S LIFETIME; failure raises `RuntimeError("Knowledge engine already running in another process. Start with --workers 1")`.

### Decisive source
```python
# engine.py:1760-1766 — acquire at CONSTRUCTION, not first use
self._lock_file = open(config.persist_dir / ".lock", "w+b")
try:
    acquire_exclusive_nonblocking(self._lock_file)
except OSError:
    self._lock_file.close()
    raise RuntimeError("Knowledge engine already running in another process. ...")
# :1785-1790 — why the thread lock exists alongside the file lock
# Serializes _ensure_embeddings across its callers (probe, per-collection
# resolve, ingest tokenizer — several run in to_thread workers). Without
# it two callers can both pass the `is None` check and load the model
# twice (duplicate ONNX session + download). HF file-locking protects the
# blob, not a double load.
```
The two locks solve different races: flock is cross-PROCESS (single-writer invariant for the whole engine), while `_embedder_init_lock` is cross-THREAD within the process (lazy init racing among to_thread workers). A cold cache means a multi-hundred-MB model download; reporting that as "unavailable" makes first runs look broken — hence `_embedder_initializing` lets health report "preparing" instead of erroring. Release swallows OSError (unlocking an already-dead fd must never mask the real error path).

**Flow:** engine construction → open `.lock` → non-blocking exclusive flock → OSError ⇒ refuse to start (loud, actionable message) → all later work assumes sole ownership. Embedder: `is None` check under thread lock → load once → health reports preparing while downloading.
**Invariant:** Exactly one engine process per persist_dir, enforced before ANY state is built; a failed lock acquisition must abort startup, not retry. The flock file handle stays open for the process lifetime — closing it releases the lock.

**Probe:** No dedicated unit test for the flock path in tests/unit — coverage caveat: multi-process behavior is integration-only by nature; `interprocess_lock` has platform branches that need both OSes to verify. Read source when porting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "acquire_exclusive_nonblocking KnowledgeEngine lock persist_dir", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt construction-time flock ownership with loud refusal, plus the separate thread-mutex for expensive lazy singletons. Adapt lock location to your state dir. Omit the msvcrt branch only if you're Unix-only.
