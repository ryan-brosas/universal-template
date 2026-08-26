<!-- capsule-v2 -->
# jb pytest nodepath translation runner — IDE tree clicks become pytest invocations how?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214 (non-git; freshness = product-info.json buildNumber re-read unchanged); Codebase Memory project `jetbrains-pycharm` (full mode, 103533 nodes). **Question:** What contract turns filesystem test paths into pytest targets while keeping IDE-visible output?

## Separator translation grammar + teamcity double-load guard + quiet shaping
**Path/Symbol:** `plugins/python-ce/helpers/pycharm/_jb_pytest_runner.py`:54-104 (__main__ body); helpers/pycharm/teamcity/pytest_plugin.py:34-36 (`set_skip_passed_output_default`), :44-57 (`pytest_addoption`).
**Signature:** `jb_patch_separator(targets, fs_glue="/", python_glue="::", fs_to_python_glue=".py::")`; doctest variant `jb_patch_targets(targets, '/', '::', '.py::', _add_module_to_target)`.
**Data Shape:** argv in/out; env `_JB_PPRINT_PRIMITIVES=1`; flags `--jb-skippassedoutput-default`, `--jb-report-logs-as-test-log`, `--jb-show-summary` consumed then stripped.

### Decisive source
```python
joined_targets = jb_patch_separator(targets, fs_glue="/", python_glue="::", fs_to_python_glue=".py::")
joined_targets = [t + ".py" if ":" not in t else t for t in joined_targets]
...
if not get_plugin_manager().hasplugin("pytest-teamcity"):
    if "pytest-teamcity" not in map(lambda e: e.name, iter_entry_points(group='pytest11')):
        plugins_to_load.append(pytest_plugin)
...
elif int(pytest.__version__.split('.')[0]) >= 6:
    args += ["--no-header", "--no-summary", "-q"]
...
os.environ["_JB_PPRINT_PRIMITIVES"] = "1"
try:
    sys.exit(pytest.main(args, plugins_to_load + [Plugin]))
finally:
    jb_finish_tests()
```

**Flow:** parse_arguments() splits workdir/targets/extras → translate each IDE tree path to a pytest node id (dir/a.b.Class.f becomes a/b.py::Class::f) → assemble argv (bare files get .py appended) → load teamcity pytest plugin ONLY if neither pytest already has it nor the pytest11 entry-point group declares it → shape quiet args on pytest>=6 unless --jb-show-summary → Plugin.pytest_configure starts the TeamCity protocol and flips parallel mode when numprocesses present → run pytest.main → finally jb_finish_tests().
**Invariant:** Translation grammar is exact (fs slash maps to python double-colon with .py:: bridge); NEVER register the teamcity plugin twice (double service messages otherwise); protocol start belongs in configure, finish in finally.
**Probe:** executed 2026-08-25 — PASS node-path separator grammar / teamcity double-load guard / pytest>=6 quiet shaping / pprint primitives env.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "pytest_plugin set_skip_passed_output_default teamcity helpers pycharm", limit: 5 });
// -> set_skip_passed_output_default @ helpers/pycharm/teamcity/pytest_plugin.py:34-36; EchoTeamCityMessages.__init__ :110-125 — EXECUTED
```

## Verdict
Adopt the three-glue contract (translate, guard, shape) for any IDE-driven pytest bridge. Adapt glue tokens to your host's node syntax. Omit doctest-module special casing if your host lacks it.