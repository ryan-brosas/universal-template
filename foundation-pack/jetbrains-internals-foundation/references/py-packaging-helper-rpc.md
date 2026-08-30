<!-- capsule-v2 -->
# Python packaging helper RPC — what protocol must an IDE-side package manager speak when it delegates pip/conda work to a helper script inside the TARGET environment?

**Source:** JetBrains DataSpell installed build `DS-261.26222.84`, plugins/python-ce/helpers plane (Apache-2.0-headered helper sources shipped inside the proprietary install). Codebase Memory `jetbrains-dataspell`. **Question:** How do `packaging_tool.py` / `conda_packaging_tool.py` report failures and stream results back across the process boundary?

## Verb-dispatched argv + numeric error codes + in-process pip execution
**Path/Symbol:** `plugins/python-ce/helpers/packaging_tool.py:run_pip` (:58-67), `error_no_pip` (:35-40), `do_install` (:50-51), `do_uninstall` (:54-55); `plugins/python-ce/helpers/conda_packaging_tool.py:main` (:96-122), `do_list_available_packages` (:14-43).
**Signature:** `packaging_tool.py <list|list_outdated|install|uninstall|pyvenv> [args…]`; exit codes `ERROR_WRONG_USAGE=1, ERROR_NO_PIP=2, ERROR_NO_SETUPTOOLS=3, ERROR_EXCEPTION=4`; `conda_packaging_tool.py listall|channels|versions <pkg>`.
**Data Shape:** stdout carries DATA only (`pip list --format=json`; conda rows as TAB-separated `name\tversion\tdep:dep:dep\n` flushed per row); stderr carries human error text; the exit code is the machine-readable failure class. Module top-level sets `os.putenv("PIP_REQUIRE_VIRTUALENV", "false")` so pip obeys the IDE even inside venvs that would otherwise refuse.

### Decisive source
```python
def run_pip(args):                     # packaging_tool.py:58-67
    import runpy
    sys.argv[1:] = args
    module_name = 'pip.__main__' if sys.version_info < (2, 7) else 'pip'
    try:
        runpy.run_module(module_name, run_name='__main__', alter_sys=True)
    except ImportError:
        error_no_pip()                 # distinguishes ERROR_NO_PIP(2) vs traceback -> 4

def main():                            # conda_packaging_tool.py:96-122 (abridged)
    cmd = sys.argv[1]
    if cmd == 'listall':
        if len(sys.argv) != 2: usage()   # arity check per verb, exit 1 on misuse
        do_list_available_packages()
    …
    except Exception:
        traceback.print_exc(); exit(ERROR_EXCEPTION)
```

**Flow:** IDE spawns the helper with the TARGET interpreter (never the IDE runtime) → verb + arity validated up front (usage error = code 1) → helper executes the real tool IN-PROCESS: pip via `runpy.run_module("pip", run_name="__main__", alter_sys=True)` so the environment's own pip and its output format are authoritative; conda via a version-laddered import of `get_index` (`conda>=22 or 4.4+: conda.core.index` / `4.2+: conda.api` / `4.1: conda.cli.main_search` / older: `common.get_index_trap()` — :27-39) → rows stream to stdout immediately (`write` + `flush` per row) so partial progress survives crashes → any exception prints traceback to stderr and exits 4.
**Invariant:** the exit-code vocabulary is the API — a porter who collapses all failures onto one non-zero code destroys the IDE's ability to distinguish "pip missing" (offer install) from "command misused" (bug) from "tool crashed" (show traceback). Equally load-bearing: data-on-stdout/errors-on-stderr separation, per-row flush, and running the env's own pip rather than bundling one (version skew becomes impossible by construction).
**Probe:** graph-live retrieval (rank-1 line-exact) plus coverage gate:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dataspell", query: "packaging_tool install uninstall pip", mode: "default", limit: 6 }); // run_pip :58-67, do_uninstall :54-55
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-dataspell", qualified_name: "jetbrains-dataspell.plugins.python-ce.helpers.conda_packaging_tool.main" }); // verbatim :96-122
await mcp.codebase_memory.check_index_coverage({ project: "jetbrains-dataspell", paths: ["plugins/python-ce/helpers/packaging_tool.py", "plugins/python-ce/helpers/conda_packaging_tool.py"] }); // no_recorded_issue x2
```

## Verdict
Adopt: helper-script delegation = verb argv + typed small-int exits + stdout-is-data discipline + in-process execution of the target env's own tool + version-laddered imports when the host library's API moved. Adapt verbs/codes to your domain. Omit py2 shims (`py2only/` docutils twins, `sys.version_info < (2,7)` branches) unless you must support fossil interpreters.
