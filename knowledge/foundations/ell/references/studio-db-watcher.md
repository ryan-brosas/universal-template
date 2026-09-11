<!-- capsule-v2 -->
# studio db watcher — how does the UI learn about new invocations without polling the database contents?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** How do I push "data changed" events to browser clients from a process that does not own the writer?

## file-stat polling + websocket broadcast
**Path/Symbol:** `src/ell/studio/__main__.py:db_watcher` (:74-107), wiring :124-131; broadcast path `src/ell/studio/connection_manager.py:ConnectionManager` (:4-18); server hook `src/ell/studio/server.py:notify_clients` (:198-203).
**Signature:** `async def db_watcher(db_path: Path, app)` — 0.1s fixed poll; `broadcast(message: str)` fans out to active websockets.
**Data Shape:** event payload is a tiny JSON `{"entity": entity, "id": id}` with entity `"database_updated"`; clients re-fetch on receipt.

### Decisive source
```python
# __main__.py:86-98
time_threshold = 0.1  # 1 second threshold
time_changed = abs(current_stat.st_mtime - last_stat.st_mtime) > time_threshold
size_changed = current_stat.st_size != last_stat.st_size
inode_changed = current_stat.st_ino != last_stat.st_ino

if time_changed or size_changed or inode_changed:
    logger.info(...)
    await app.notify_clients("database_updated")

last_stat = current_stat
except FileNotFoundError:
    if last_stat is not None:
        logger.info(f"Database file deleted: {db_path}")
        await app.notify_clients("database_updated")
last_stat = None
await asyncio.sleep(1)  # Wait a bit longer if the file is missing
```

**Flow:** uvicorn runs on a manually-created event loop (`loop.create_task(server.serve())`, `run_forever`) so the watcher task shares it. Each tick stats the SQLite file; mtime delta beyond threshold OR size change OR inode swap (atomic-replace writers!) triggers broadcast; first sighting announces and notifies immediately; deletion notifies then backs off to 1s polls until the file returns. The server attaches the async broadcaster onto the FastAPI app object itself so any request handler can notify (used by write-side endpoints in some deployments).
**Invariant:** three independent change signals because SQLite writers differ — WAL touch-ups bump mtime without size change, atomic replace swaps inode; watching only one signal misses real writes. The watcher never reads DB contents: cheap, lock-free, works across processes.
**Probe:** deterministic anchors from repo root: `grep -c 'st_ino' src/ell/studio/__main__.py` == 2 (read + log); `grep -n 'database_updated' src/ell/studio/__main__.py` → :84, :98, :104 (found-first, changed, deleted). No direct unit test at pin (needs a live loop+socket — coverage caveat recorded honestly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "broadcast websocket active connections", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.src.ell.studio.connection_manager.ConnectionManager.broadcast @ src/ell/studio/connection_manager.py:15-18
```

## Verdict
Adopt stat-signal fan-in for cross-process change detection. Adapt poll interval/thresholds to your freshness needs and swap websockets for SSE if you prefer one-way. Omit the print-inside-broadcast debug noise upstream still carries.
