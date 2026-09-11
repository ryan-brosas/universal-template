<!-- capsule-v2 -->
# FIFO named-pipe log streaming — how do you stream agent logs to an external process without blocking it?

**Source:** browser-use MIT `main@85ddbfedf609166b2d2c76c3d80506649fee82a9`; Codebase Memory `mnt-hdd-utopia-inspo-agents-browser-use`. **Question:** how does `setup_log_pipes` expose agent/CDP/event logs as tail-able pipes that never block the event loop?

## Lazy-open non-blocking FIFO handler
**Path/Symbol:** `browser_use/logging_config.py:237-329` (`FIFOHandler` :237, `setup_log_pipes` :282).
**Signature:** `FIFOHandler(fifo_path: str)` (logging.Handler subclass); `setup_log_pipes(session_id: str, base_dir: str | None = None)`.
**Data Shape:** three pipes under `{base_dir|tmp}/buagent.{session_id[-4:]}/`: `agent.pipe` (DEBUG; loggers `browser_use.agent`, `browser_use.tools`), `cdp.pipe` (DEBUG; `websockets.client`, `cdp_use.client`), `events.pipe` (INFO; `bubus`, `browser_use.browser.session`). Frame format `%(levelname)-8s [%(name)s] %(message)s\n`.

### Decisive source
```python
def emit(self, record):
    try:
        if self.fd is None:                       # open lazily on FIRST write
            try:
                self.fd = os.open(self.fifo_path, os.O_WRONLY | os.O_NONBLOCK)
            except OSError:
                return                            # no reader yet → skip message silently
        msg = f'{self.format(record)}\n'.encode()
        os.write(self.fd, msg)
    except (OSError, BrokenPipeError):            # reader disconnected → reset
        if self.fd is not None:
            ...os.close(self.fd)...               # next emit re-opens
            self.fd = None
```

**Flow:** create FIFO if missing (`os.mkfifo`) but do NOT open → on each record, open `O_WRONLY|O_NONBLOCK` on first use; with no reader connected open raises and the record is DROPPED → writes are non-blocking so a stalled consumer can never freeze the agent loop → broken pipe closes the fd for lazy re-open. Pipe dir name uses only the LAST FOUR chars of session_id.
**Invariant:** logging must never block or raise into the emitter — drop-on-no-reader and reset-on-broken-pipe keep producer latency O(write); consumers attach/detach freely (`tail -f …agent.pipe`) without any producer-side lifecycle. Handlers attach to named loggers with `propagate=True` so records ALSO reach the console setup.
**Probe:** no upstream unit test covers this module (coverage caveat — demo-mode consumer only). Deterministic probe: `python3 -c "import inspect, browser_use.logging_config as m; src=inspect.getsource(m.FIFOHandler.emit); assert 'O_NONBLOCK' in src and 'BrokenPipeError' in src"` from a checkout.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-browser-use", query: "FIFOHandler setup_log_pipes os.mkfifo O_NONBLOCK", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the lazy-open/non-blocking/drop-on-absent-reader FIFO handler verbatim for out-of-process observability. Adapt pipe naming and which loggers feed which pipe. Omit nothing — opening eagerly at construction would block forever when no consumer has attached yet.
