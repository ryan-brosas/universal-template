<!-- capsule-v2 -->
# Jupyter cell debug-id map — how do IDE breakpoints expressed as (cell-content-hash, line) find their frame inside a live IPython kernel?

**Source:** JetBrains DataSpell installed build `DS-261.26222.84`, `plugins/python-ce/helpers/jupyter_debug` plane. Codebase Memory `jetbrains-dataspell`. **Question:** When the IDE only knows notebook cells by content, what kernel-side mechanism translates a `.py` frame filename back to a cell identity so breakpoints and exceptions suspend the right line?

## sha256(cell_content) ↔ generated-filename map built lazily from linecache at first breakpoint hit
**Path/Symbol:** `plugins/python-ce/helpers/jupyter_debug/pydev_jupyter_utils.py` — `JupyterDebugCellInfo.cache_cell_mapping` (:31-40), module-level `is_cell_filename` (:113-134), `attach_to_debugger` (:73-95); `pydev_jupyter_plugin.py` — `get_breakpoint` (:190-206), `_is_inside_jupyter_cell` (:229-241), `send_cell_modified_warning_once` (:222-226).
**Signature:** `JupyterDebugCellInfo.cell_filename_to_cell_id_map: dict[str, str]`; `attach_to_debugger(debugger_port)`; `get_breakpoint(plugin, pydb, frame, event, args) -> tuple | False`; breakpoint payload from the IDE side is `(cell_id=sha256(cell_content), line)`.
**Data Shape:** each executed IPython cell materializes a synthetic `.py` file whose source lives in `linecache`. Classification ladder (`is_cell_filename`): IPython <8 → membership in `linecache._ipython_cache`; ≥8 → `linecache.cache` entry with `cached_value[1] is None` meaning user code (not library); both exclude entries whose first source line contains `"pydev_util_command"` (the plugin's own probes). The private classifier used while caching (`__is_cell_filename`) checks ONLY `filename in linecache.cache`.

### Decisive source
```python
def cache_cell_mapping(self, cell_filename):        # pydev_jupyter_utils.py:31-40
    try:
        if not self.__is_cell_filename(cell_filename): return
        cell_content = self.__get_cell_content(cell_filename)   # "".join(linecache.cache[f][2])
        self.cell_filename_to_cell_id_map[cell_filename] = \
            self.__compute_cell_content_hash(cell_content)      # sha256(content).hexdigest()
    except Exception as _:
        pass

def get_breakpoint(plugin, pydb, frame, event, args):           # pydev_jupyter_plugin.py:190-206
    filename = frame.f_code.co_filename; frame_line = frame.f_lineno
    if event == "line" and hasattr(pydb, 'cell_info'):
        if is_cell_filename(filename):
            if filename not in cell_info.cell_filename_to_cell_id_map:
                cell_info.cache_cell_mapping(filename)          # LAZY fill on first hit
            cell_id = cell_info.cell_filename_to_cell_id_map[filename]
            if cell_id in pydb.jupyter_breakpoints:
                line_to_bp = pydb.jupyter_breakpoints[cell_id]
                if frame_line in line_to_bp:
                    return True, line_to_bp[frame_line], frame, "jupyter-line"
    return False

def attach_to_debugger(debugger_port):                          # :73-95 (abridged)
    debugger = pydevd.PyDB()
    debugger.frame_eval_func = None                             # frame-eval unusable on exec'd cell code
    debugger.connect(...); debugger.prepare_to_run(enable_tracing_from_start=False)
    if not hasattr(ipython_shell, "pydev_cell_info"):
        ipython_shell.pydev_cell_info = JupyterDebugCellInfo()  # once per kernel
    debugger.cell_info = ipython_shell.pydev_cell_info
    debugger.warn_once_map = {}
```

**Flow:** IDE computes `kotlin_cell_id = sha256(cell_content)` for every cell holding a breakpoint and ships `(cell_id, line)` pairs into `pydb.jupyter_breakpoints` → kernel-side `attach_to_debugger` installs a plain-tracing PyDB (frame-eval off, tracing-from-start off) and pins ONE `JupyterDebugCellInfo` onto the ipython shell → when a traced line event lands in a cell file, `get_breakpoint` lazily hashes the linecache source into the map, looks up `jupyter_breakpoints[cell_id][line]`, and reports bp type `"jupyter-line"` → `suspend()` wraps the frame in a `JupyterFrame` and suspends with `JUPYTER_SUSPEND` type → a frame whose file is a cell but NOT in the map (cell edited after the IDE sent breakpoints) triggers `send_cell_modified_warning_once` and is ignored.
**Invariant:** cell identity = content hash, so re-running an unchanged cell keeps its breakpoints while editing a cell invalidates them BY CONSTRUCTION (warning-once instead of silent drop); classification must reject libraries and the plugin's own util commands or every library import would match cell breakpoints; caching failures are swallowed (`except: pass`) because a failed mapping just means "no breakpoints here".
**Probe:** graph-live retrieval + coverage gate + direct read (all executed this pass):
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dataspell", query: "jupyter_debug cell id linecache ipython cache breakpoint kotlin_cell_id" });
// rank hits: cache_cell_mapping :31-40, is_cell_filename :113-134 & :280-300, get_breakpoint :190-206
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-dataspell", qualified_name: "jetbrains-dataspell.plugins.python-ce.helpers.jupyter_debug.pydev_jupyter_utils.JupyterDebugCellInfo.cache_cell_mapping" }); // verbatim
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-dataspell", paths: ["plugins/python-ce/helpers/jupyter_debug/pydev_jupyter_utils.py", "plugins/python-ce/helpers/jupyter_debug/pydev_jupyter_plugin.py"] }); // no_recorded_issue x2
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dataspell", query: "suspend jupyter exception break convert filename", limit: 8 }); // suspend_jupyter :209-219, exception_break :257-269, _convert_filename :272-277
```

## Verdict
Adopt: content-hash cell identity + lazy linecache-derived filename→id map + warn-once stale-cell policy + trace-based (never frame-eval) debugging of exec'd cell code + first-line sentinel ("pydev_util_command") to exclude probe code. Adapt the hash key to whatever your host uses as stable cell identity. Omit the IPython <8 `_ipython_cache` rung unless you support fossil kernels; note the two classifiers differ (private one omits the version ladder) — port the STRICT public one.
