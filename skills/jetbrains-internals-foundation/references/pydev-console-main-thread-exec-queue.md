<!-- capsule-v2 -->
# pydev console main-thread exec queue — how do RPC threads execute code safely inside a REPL?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214; Codebase Memory project `jetbrains-pycharm`. **Question:** How should foreign threads (RPC handlers, debugger) mutate a live interpreter namespace without races?

## Buffer on callers, serialize through one queue, run closures in the interpreter thread
**Path/Symbol:** `plugins/python-ce/helpers/pydev/_pydev_bundle/pydev_code_executor.py`:16-23 `BaseCodeExecutor.__init__`; :57-63 `need_more`; :68-134 `add_exec`; `pydevconsole.py`:251-296 `process_exec_queue`; `pydev_console_utils.py`:117-129 `do_exec_code`.
**Signature:** `add_exec(code_fragment, debugger=None) -> (more, exception_occurred)`; queue entries are `CodeFragment` OR zero-arg callables.
**Data Shape:** unbounded `_queue.Queue(0)`; `self.buffer` holds incomplete multi-line input until complete.

### Decisive source
```python
# process_exec_queue — the ONLY consumer, 20 polls/sec
code_fragment = interpreter.exec_queue.get(block=True, timeout=1/20.)
...
if hasattr(code_fragment, '__call__'):
    code_fragment()          # closures (changeVariable, enableGui, connectToDebugger)
else:
    interpreter.add_exec(code_fragment)

# add_exec — tracing window covers ONLY user code
self.start_exec()
if hasattr(self, 'debugger'):
    pydevd_tracing.SetTrace(self.debugger.trace_dispatch)
more, exception_occurred = self.do_add_exec(code_fragment)
if hasattr(self, 'debugger'):
    pydevd_tracing.SetTrace(None)
```
Callers never exec directly: `do_exec_code` enqueues only when `need_more` says the buffered text is complete (`is_complete()` / compile(); backslash continuation always "more").

**Flow:** front-end RPC → buffer/validate → enqueue fragment-or-closure → main loop drains at 20 Hz (parent-liveness watchdog `PYDEV_ECLIPSE_PID` first) → stdin swapped to `StdIn` wrapper for the duration → optional tracing window → run → `finish_exec` notifies front-end (`server.notifyFinished(more, exception_occurred)`).
**Invariant:** All namespace mutation and all execution happen in the ONE interpreter thread; anything else is expressed as a closure in the queue. Debugger tracing is scoped per-command, never left enabled between commands.
**Probe:** executed 2026-08-25 — PASS: order `SetTrace(trace_dispatch)` < `do_add_exec` < `SetTrace(None)` in shipped source; `_queue.Queue(0)` precedes buffering logic; `exec_queue.put(do_enable_gui)` and `put(do_change_variable)` prove closure-scheduling; stdin swap present. (First probe draft wrongly asserted `put(code_fragment)` lives in pydev_code_executor — it lives in pydev_console_utils.do_exec_code; corrected against source.)

## Get live surrounding code
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-pycharm", qualified_name: "jetbrains-pycharm.plugins.python-ce.helpers.pydev._pydev_bundle.pydev_code_executor.BaseCodeExecutor.add_exec" });
// -> start_line 68 end_line 134 — EXECUTED
```

## Verdict
Adopt: single-consumer command queue with callable entries, caller-side completeness buffering, per-command tracing window, parent-PID orphan watchdog. Adapt poll rate/stdin plumbing. Omit Jython line-by-line execMultipleLines path and pydoc.help defensive branches if your host has none.
