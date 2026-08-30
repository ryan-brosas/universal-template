<!-- capsule-v2 -->
# pydev console debugger virtual frame — how does a variables view read a REPL namespace through a debugger protocol?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214; Codebase Memory project `jetbrains-pycharm`. **Question:** How can the debugger's variable/evaluate machinery work against a console that has no real stack frames?

## Serve a FakeFrame whose f_locals IS the namespace; attach with tracing OFF; ride the idle hook
**Path/Symbol:** `plugins/python-ce/helpers/pydev/_pydev_bundle/pydev_console_utils.py`:332-345 `_findFrame`; :347-413 `connectToDebugger`; :480-484 `FakeFrame`; `pydevconsole.py`:123-128 `_ProcessExecQueueHelper.set_debug_hook`.
**Signature:** `connectToDebugger(debuggerPort, debugger_host=None, debugger_options=None, extra_envs=None) -> ('connect complete',)`.
**Data Shape:** reserved ids: thread `"console_main"`, frame `"1"` (must match IDE-side `PyThreadConsole.java` / `PyStackFrameConsole.java`).

### Decisive source
```python
VIRTUAL_FRAME_ID = "1"; VIRTUAL_CONSOLE_ID = "console_main"
if thread_id == VIRTUAL_CONSOLE_ID and frame_id == VIRTUAL_FRAME_ID:
    f = FakeFrame()
    f.f_globals = {}                       # empty on purpose — save network traffic
    f.f_locals = self.get_namespace()
    return f

# inside do_connect_to_debugger (enqueued to main thread):
set_thread_id(threading.current_thread(), "console_main")
self.orig_find_frame = pydevd_vars.find_frame
pydevd_vars.find_frame = self._findFrame   # monkeypatch the resolver
self.debugger = pydevd.PyDB()
self.debugger.connect(host, debuggerPort); self.debugger.prepare_to_run()
self.debugger.disable_tracing()            # attach WITHOUT tracing user frames
pydevconsole.set_debug_hook(self.debugger.process_internal_commands)  # idle hook
```

**Flow:** RPC call → enqueue closure → rename thread → patch `find_frame` → build+connect PyDB → prepare then DISABLE tracing → register `process_internal_commands` as debug hook → from then on every exec-queue poll first calls the hook, so debugger commands are processed between user commands.
**Invariant:** The pair (`console_main`, `1`) is a wire contract with the Java side — changing either silently breaks the variables view. Attach must not enable global tracing; command processing happens only at queue-poll boundaries.
**Probe:** executed 2026-08-25 — PASS: both sentinel id strings present verbatim; `find_frame` monkeypatch, `prepare_to_run()` + `disable_tracing()` ordering, `set_debug_hook(...process_internal_commands)` and main-thread enqueue of `do_connect_to_debugger` all confirmed in shipped source.

## Get live surrounding code
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-pycharm", qualified_name: "jetbrains-pycharm.plugins.python-ce.helpers.pydev._pydev_bundle.pydev_console_utils.BaseInterpreterInterface.connectToDebugger" });
// -> start_line 347 end_line 413 — EXECUTED
```

## Verdict
Adopt: fake-frame indirection keyed by reserved thread/frame ids + idle-hook command processing + tracing-off attach. Adapt id strings to your front-end's constants. Omit Jython import fallbacks and env-append semantics of `extra_envs` if unneeded.
