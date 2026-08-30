<!-- capsule-v2 -->
# jb unittest runner dispatch ladder — how do you map IDE run targets onto unittest's CLI without discovery flakiness?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214; Codebase Memory project `jetbrains-pycharm`. **Question:** What dispatch order makes `python -m unittest` honor file targets (including hyphenated names) while still supporting folders and dotted targets?

## Direct-file run on Py3; discover with top-level dir otherwise; TeamCity runner + buffering gate
**Path/Symbol:** `plugins/python-ce/helpers/pycharm/_jb_unittest_runner.py`:15-63 `build_unittest_args`; :66-83 `main`; `_jb_runner_tools.py`:369-375 `jb_start_tests`, :392-425 `parse_arguments`.
**Signature:** `build_unittest_args(path, targets, additional_args, project_dir=PROJECT_DIR, verbose=JB_VERBOSE) -> list[str]`.
**Data Shape:** IDE sends either `--path` (file or folder) or repeated `--target` (dotted), plus `--offset` and post-`--` passthrough args.

### Decisive source
```python
if sys.version_info >= (3, 0) and os.path.isfile(path):
    # in Py3 it is possible to run script directly which is much more stable
    # than discovery machinery — e.g. it supports hyphens in file names PY-23549
    subcommand_args = [path]
else:
    subcommand_args = ["discover", "-s"]
    if os.path.isfile(path):
        subcommand_args += [os.path.dirname(path), "-p", os.path.basename(path)]
    else:
        subcommand_args.append(path)
    subcommand_args += ["-t", project_dir]     # force relative-to-project resolution
...
sys.exit(unittest_main(argv=args, module=None,
                       testRunner=unittestpy.TeamcityTestRunner,
                       buffer=not JB_DISABLE_BUFFERING))
```
`main()` inserts PROJECT_DIR at sys.path[0] ("that is how unittest work when launched from command line") and wraps the run in try/finally → `jb_finish_tests()`.

**Flow:** `jb_start_tests` (parse + start protocol) → build args ladder: path+Py3+file → direct script; path+file otherwise → discover scoped by `-p` pattern with `-t` top-level; path=folder → discover; no path → pass dotted targets through → verbose flag (`--verbose`/`--quiet`) → run under TeamcityTestRunner so the patched service-messages kernel reports node ids.
**Invariant:** Never route a Py3 file target through `discover` (hyphen filenames break it). The exit-time suite close must run even when unittest_main raises (finally).
**Probe:** executed 2026-08-25 — PASS: PY-23549 comment + isfile branch verbatim; `discover -s ... -t` construction present; `testRunner=unittestpy.TeamcityTestRunner`; `buffer=not JB_DISABLE_BUFFERING`; finally-wrapped finish. Retrieve pinned `build_unittest_args` at :15-63 via search_graph.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", name_pattern: "build_unittest_args|jb_start_tests" });
// -> _jb_unittest_runner.build_unittest_args :15-63 ; _jb_runner_tools.jb_start_tests :369-375 — EXECUTED
```

## Verdict
Adopt: direct-file-first dispatch with discovery fallback carrying `-p` pattern + `-t` project root; sys.path restoration of the working dir; runner injection point for the reporting kernel. Adapt flag spellings per unittest version. Omit py2-only branches once your floor ≥3.
