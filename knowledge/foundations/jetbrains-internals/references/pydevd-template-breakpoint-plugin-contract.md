<!-- capsule-v2 -->
# pydevd template breakpoint plugin contract — add framework breakpoints without touching kernel dispatch?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214 (non-git; freshness = product-info.json buildNumber re-read unchanged); Codebase Memory project `jetbrains-pycharm` (full mode, 103533 nodes). **Question:** How does a framework (Django/Jinja2) hook its own line/exception breakpoints into the debugger core?

## Type-string routing with None-means-not-mine fallback
**Path/Symbol:** `plugins/python-ce/helpers/pydev/pydevd_plugins/django_debug.py`:39-53 (`add_line_breakpoint`/`add_exception_breakpoint`); twin `jinja2_debug.py`.
**Signature:** `add_line_breakpoint(plugin, pydb, type, file, line, condition, expression, func_name, hit_condition=None, is_logpoint=False) -> (DjangoLineBreakpoint, dict) | None`.
**Data Shape:** breakpoint types are STRINGS: `'django-line'`, `'django'`; jinja twins `'jinja2-line'`, `'jinja2'`. Per-plugin state lives lazily on the debugger object (`pydb.django_breakpoints`, `pydb.django_exception_break`).

### Decisive source
```python
def add_line_breakpoint(plugin, pydb, type, file, line, ...):
    if type == 'django-line':
        breakpoint = DjangoLineBreakpoint(file, line, ...)
        if not hasattr(pydb, 'django_breakpoints'):
            _init_plugin_breaks(pydb)
        return breakpoint, pydb.django_breakpoints
    return None          # <- not mine: core falls through to ordinary handling

def add_exception_breakpoint(plugin, pydb, type, exception):
    if type == 'django':
        ...
        return True
    return False
```
Template frames suspend with a distinct state: imports pair `STATE_SUSPEND` with `DJANGO_SUSPEND` (:3) — stepping logic treats template suspension separately from PYTHON suspend.

**Flow:** IDE sends CMD_SET_BREAK / django exception-break commands → core asks each plugin function → plugin claims by type string and stores into its lazy per-pydb dicts → at trace time template remapping consults `breakpoint.is_triggered(template_frame_file, template_frame_line)` (:29-30). Django version flags probe lazily inside try/import (`IS_DJANGO18/19/19_OR_HIGHER`, :11-21).
**Invariant:** A plugin MUST answer every call; `None`/`False` means "not mine" so multiple frameworks coexist. Breakpoint identity for templates is (file, line) over the TEMPLATE path, not the rendered Python path.
**Probe:** executed 2026-08-25 — `PASS django-line type routing / PASS DJANGO_SUSPEND state / PASS jinja2-line twin`.
**Coverage caveat:** direct read + check_index_coverage no_recorded_issue for django_debug.py (EXECUTED).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-pycharm", qualified_name: "jetbrains-pycharm.plugins.python-ce.helpers.pydev.pydevd_plugins.django_debug.add_line_breakpoint" });
// -> start_line 39 end_line 45, source confirms the None fallback — EXECUTED
```

## Verdict
Adopt claim-by-type-string with not-mine fallback and lazy per-target state init. Adapt the suspend-state vocabulary to your host's stepper. Omit Django-version ladders below your supported floor.
