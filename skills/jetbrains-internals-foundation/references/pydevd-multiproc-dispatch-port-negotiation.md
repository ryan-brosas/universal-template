<!-- capsule-v2 -->
# pydevd multiproc dispatch port negotiation — how do forked children get their own debug channel?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214 (non-git; freshness = product-info.json buildNumber re-read unchanged); Codebase Memory project `jetbrains-pycharm` (full mode, 103533 nodes). **Question:** How does a forked child learn WHICH port to attach back on without rescanning?

## Undocumented cmd 99 meta-channel over the reused connection
**Path/Symbol:** `plugins/python-ce/helpers/pydev/pydevd.py`:2022-2025 `DispatchReader.process_command`; :2028-2033 `_should_use_existing_connection`; :2036-2047 `dispatch`; :2255-2277 `main()` multiproc branch.
**Signature:** `def process_command(self, cmd_id, seq, text): if cmd_id == 99: self.dispatcher.port = int(text); self._kill_received = True`.
**Data Shape:** child opens the PARENT's negotiated IDE port; the dispatcher reader consumes frames until id 99 whose TEXT payload is the new port digits.

### Decisive source
```python
def process_command(self, cmd_id, seq, text):
    if cmd_id == 99:
        self.dispatcher.port = int(text)
        self._kill_received = True

def _should_use_existing_connection(setup):
    """The new connection dispatch approach is used by PyDev when the `multiprocess` option is set,
    the existing connection approach is used by PyCharm when the `multiproc` option is set."""
    return setup.get('multiproc', False)
```

**Flow:** `main()` with `--multiproc` → `Dispatcher()` connects to the IDE's dispatch port → synchronous `reader.run()` reads until 99 arrives → `dispatch()` returns `(host, new_port)` → `settrace_forked()` resets `GlobalDebuggerHolder.global_dbg = None` + `connected=False` then calls `settrace(host, port=new_port, patch_multiprocessing=True, ...)`. PyDev-style `--multiprocess` instead patches process functions so each child dials a fresh listener directly.
**Invariant:** Two sibling vocabularies coexist by design: `multiprocess` (upstream PyDev, NEW connection per child) vs `multiproc` (PyCharm, EXISTING-connection negotiation). Command id 99 sits BELOW the documented 101+ range and appears in neither `CMD_*` nor `ID_TO_MEANING` — it is the reserved dispatch-meta slot; never collide with it when extending the table.
**Probe:** executed 2026-08-25 — `PASS cmd_id==99 port dispatch / PASS PyCharm multiproc existing-connection / PASS main multiproc dispatcher branch / PASS settrace_forked resets global_dbg` (regex/substring battery from install root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-pycharm", qualified_name: "jetbrains-pycharm.plugins.python-ce.helpers.pydev.pydevd.DispatchReader.process_command" });
// -> start_line 2022 end_line 2025, source shows the cmd_id == 99 port capture — EXECUTED
```

## Verdict
Adopt the negotiate-over-existing-channel pattern (parent hands children their endpoints) and keeping meta commands in a low reserved band. Adapt the payload encoding. Omit the app-engine restart special-casing around it.