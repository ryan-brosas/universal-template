<!-- capsule-v2 -->
# Supervisor dispatch and import-string gate — when must the app be a string, and who binds the socket?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** How does `run()` decide between inline server, ChangeReload, and Multiprocess — and why do the latter two REQUIRE an import string?

## run() dispatch + STARTUP_FAILURE exit contract
**Path/Symbol:** `uvicorn/main.py:run` (:596–631); gate :602–608; UDS cleanup in `finally` (:625–626); exit contract :630–631.
**Signature:** `def run(app: ASGIApplication | Callable | str, *, host=..., port=..., reload=False, workers=None, ...) -> None`.
**Data Shape:** `STARTUP_FAILURE = 3` (uvicorn/config.py:97) is BOTH the child-process exit code AND the parent's CLI exit code; `config.should_reload == isinstance(self.app, str) and self.reload`.

### Decisive source
```python
# :602-619 — string-gate then supervisor choice
if config.reload or config.workers > 1:
    if not isinstance(app, str):
        logger.warning("You must pass the application as an import string to enable 'reload' or 'workers'.")
        sys.exit(STARTUP_FAILURE)
else:
    config.load_app()          # only inline mode imports eagerly here

server = Server(config=config)
try:
    if config.should_reload:
        sock = config.bind_socket()
        ChangeReload(config, target=server.run, sockets=[sock]).run()
    elif config.workers > 1:
        sock = config.bind_socket()
        Multiprocess(config, sockets=[sock]).run()
    else:
        server.run()
...
finally:
    if config.uds and os.path.exists(config.uds):
        os.remove(config.uds)
if not server.started and not config.should_reload and config.workers == 1:
    sys.exit(STARTUP_FAILURE)
```

**Flow:** app object + reload/workers ⇒ refuse with exit 3 (spawned children re-import the app by string; a live object cannot cross process boundaries) → parent binds the shared socket ONCE (`bind_socket()` sets SO_REUSEADDR + `set_inheritable(True)`) → supervisor owns restarts → on unwind remove the UDS file even after crash (finally). Inline single-process startup failure surfaces as exit 3 via the trailing `not server.started` check.
**Invariant:** Socket binding happens in the PARENT exactly once for both supervisors; children inherit via spawn pickling of sockets (`multiprocessing.allow_connection_pickling()` in `_subprocess.py:17`). The import-string requirement is structural to spawn-mode workers, not a style choice.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'Multiprocess(config, sockets=\[sock\])' uvicorn/uvicorn/main.py"` → 1; `bash -c "grep -c 'os.remove(config.uds)' uvicorn/uvicorn/main.py"` → 1; `bash -c "grep -n 'isinstance(app, str)' uvicorn/uvicorn/main.py"` → line 604.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"bind socket change reload multiprocess run dispatch","limit":5,"detail":"ids"}` → resolves `main.run` region and `Config.bind_socket` line-exact.
**Verdict:** Adopt the dispatch ladder, parent-binds-once rule, and exit-code-3 contract verbatim. Adapt flag names. Omit click plumbing (envvar prefix UVICORN_ etc.).

