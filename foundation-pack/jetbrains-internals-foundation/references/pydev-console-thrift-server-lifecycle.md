<!-- capsule-v2 -->
# pydev console thrift server lifecycle — how does the IDE talk to a live Python REPL process?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214 (non-git; freshness = product-info.json buildNumber re-read unchanged 2026-08-25); Codebase Memory project `jetbrains-pycharm`. **Question:** What process model and handshake let an IDE own a remote interactive Python interpreter?

## Two personas, one entry point, port-on-stdout handshake
**Path/Symbol:** `plugins/python-ce/helpers/pydev/pydevconsole.py`:434-468 `start_server`; :471-498 `start_client`; :385-399 `do_exit`; :536-572 `__main__`.
**Signature:** `start_server(port)` / `start_client(host, port)`; CLI `-m {client,server} [-h host] [-p port]`.
**Data Shape:** server mode binds `''` with port 0 when None; the BOUND port is printed to stdout as the sole handshake payload; both modes end in the never-returning `process_exec_queue(interpreter)`.

### Decisive source
```python
def start_server(port):
    if port is None:
        port = 0
    sys.exit = do_exit                      # sys.exit cannot kill a server main thread
    ...
    interpreter = InterpreterInterface(threading.current_thread())
    _set_globals_function(interpreter.get_namespace)   # UMD runs against console namespace
    server_socket = start_rpc_server_and_make_client('', port, server_service, client_service,
                                                     create_server_handler_factory(interpreter))
    _, server_port = server_socket.getsockname()
    print(server_port)                      # THE handshake: IDE reads bound port from stdout
    process_exec_queue(interpreter)
```
(`do_exit` calls `os._exit`; thrift services come from `pydev_console.pydev_protocol`: `PythonConsoleBackendService` / `PythonConsoleFrontendService`.)

**Flow:** parse args → reject mode ∉ {client, server} → replace `sys.exit` → build interpreter + thrift service pair → bind/listen → print bound port (server) or connect out (client, no extra listener needed since the connection already exists) → run exec queue forever.
**Invariant:** The IDE never guesses the port; the backend publishes the OS-assigned port on stdout exactly once. Exit must be `os._exit` because a blocking RPC server main thread cannot propagate `SystemExit`.
**Probe:** executed 2026-08-25 — AST probe PASS: `sys.exit = do_exit`, `print(server_port)`, `start_rpc_server_and_make_client`, `process_exec_queue(interpreter)` all inside `start_server`; `os._exit` in `do_exit`; `PYDEV_ECLIPSE_PID` watchdog and `timeout=1/20.` poll in `process_exec_queue`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-pycharm", qualified_name: "jetbrains-pycharm.plugins.python-ce.helpers.pydev.pydevconsole.start_server" });
// -> start_line 434 end_line 468 — EXECUTED (byte-matches direct read)
```

## Verdict
Adopt: separate-process console with thrift service pair, port-via-stdout handshake, os._exit override, UMD namespace injection via `_set_globals_function`. Adapt transport (any bidirectional channel can carry the services); keep "print one machine-readable token then go silent" discipline. Omit Jython exit caveat and py2 branches.
