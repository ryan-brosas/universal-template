<!-- capsule-v2 -->
# pydev IPython shell personality — how do you embed TerminalInteractiveShell into an IDE console?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214; Codebase Memory project `jetbrains-pycharm`. **Question:** What must be overridden so IPython's terminal shell behaves inside a hosted console instead of a TTY?

## Traitlet-mute the terminal, reuse singletons, sync namespaces identity-safely
**Path/Symbol:** `plugins/python-ce/helpers/pydev/_pydev_bundle/pydev_ipython_console_011.py`:86-248 `PyDevTerminalInteractiveShell` / `PyDebuggerTerminalInteractiveShell`; :271-302 `_PyDevIPythonFrontEnd`; :309-325 `update`; :412-445 `add_exec`; :465-487 `get_pydev_ipython_frontend`; `pydev_ipython_console.py`:12-69; `pydevconsole.py`:299-321 import-time rebinding.
**Signature:** `update(globals, locals)`; `add_exec(line) -> (more, exception_occurred)`; `get_pydev_ipython_frontend(rpc_client, is_jupyter_debugger=False)`.
**Data Shape:** module-level class swap in pydevconsole (`IPythonInterpreterInterface as InterpreterInterface`) gated by env `IPYTHONENABLE` and try/except on IPython import.

### Decisive source
```python
class PyDevTerminalInteractiveShell(TerminalInteractiveShell):
    readline_use  = CBool(False)      # IDE owns line editing
    autoindent    = CBool(False)
    colors_force  = CBool(True)
    colors        = Unicode("nocolor" if IPython.version_info >= (9,) else "NoColor")
    simple_prompt = CBool(True)       # IPython>=5: not an emacs inferior-shell
    def showtraceback(self, ...):     # plain print_exc so PyDev can parse source links
    ...
def update(self, globals, locals):
    self.ipython.user_global_ns.clear(); self.ipython.user_global_ns.update(globals)
    # generator-expression corner case: identical objects must STAY identical
    self.ipython.user_ns = self.ipython.user_global_ns if globals is locals else locals
```

**Flow:** import time → if IPython importable (env gate), rebind `InterpreterInterface` to `IPythonInterpreterInterface`, whose `do_add_exec` delegates to a singleton front-end → front-end builds PyDevIpythonApp around the personality shell (reusing `_instance`/`new_instance` when present, else `clear_instance()` + fresh init) → each exec runs `ipython.run_cell` (store_history=True except debugger console) → namespace synced by `update` before evaluation → `%edit` opens files back in the IDE via `rpc_client.IPythonEditor(filename, line)`; magic catalog pushed once via `notifyAboutMagic` (max 3 tries).
**Invariant:** Never let the shell own readline/term_title/pager/color — every terminal capability must be muted or rerouted to the host. `user_ns` aliasing must preserve object identity between globals and locals when callers pass the same dict.
**Probe:** executed 2026-08-25 — PASS: identity branch string verbatim; `nocolor` for IPython≥9 vs `NoColor`; `simple_prompt CBool(True)`; singleton ladder (`new_instance` + `clear_instance()`); editor backchannel RPC; magic notify with retry cap.

## Get live surrounding code
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-pycharm", qualified_name: "jetbrains-pycharm.plugins.python-ce.helpers.pydev._pydev_bundle.pydev_ipython_console_011._PyDevIPythonFrontEnd.update" });
// -> start_line 309 end_line 325 — EXECUTED
```

## Verdict
Adopt: personality-by-subclass (traitlets over monkeypatching), singleton-reuse ladder, identity-preserving namespace sync, editor/magic backchannels over the existing RPC channel. Adapt trait names to your IPython version window; keep the ≥9 lowercase-color rename. Omit IPython<5 compat comments.
