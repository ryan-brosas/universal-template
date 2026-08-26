<!-- capsule-v2 -->
# behave dry-run feature census — how do you enumerate BDD scenarios without executing them, then run the filtered set?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214; Codebase Memory project `jetbrains-pycharm`. **Question:** How can an IDE harness get behave's parsed feature/scenario model up-front and still execute a clean second pass?

## Dry-run harvest → module-cache rollback (C extensions exempt) → clean() → real run
**Path/Symbol:** `plugins/python-ce/helpers/pycharm/behave_runner.py`:115-137 `_RunnerWrapper.run_model/clean`; :247-286 `_BehaveRunner._get_features_to_run`; :289-321 formatter registration; :324-365 `main`.
**Signature:** `_get_features_to_run(self)` (dry run + filter); `main()` CLI contract: env-driven selection via `_bdd_utils.get_what_to_run_by_env(os.environ)`.
**Data Shape:** hooks dict `"before_feature" => fn(context, element)` merged into behave's environment hooks; formatter registered under name `com.jetbrains.pycharm.formatter`.

### Decisive source
```python
old_modules = sys.modules.copy()
self.__real_runner.dry_run = True
self.__real_runner.run()                       # parses features, executes NOTHING
new_modules = sys.modules.copy()
for module in new_modules.keys():
    if module in old_modules: continue
    path = getattr(sys.modules.get(module), '__file__', None)
    if path and path.endswith(_EXT_SUFFIXES):  # .so/.pyd register global types — keep them
        continue
    del sys.modules[module]                    # pure-Python step modules: force reimport
features_to_run = self.__real_runner.features
self.__real_runner.clean()                     # clears hooks/features/step registry
```
Second pass replaces ScenarioOutline skeletons with concrete scenarios and filters by tag expression + name regex (`__filter_scenarios_by_args`).

**Flow:** build behave Configuration from argv (+ `-n re.escape(scenario)`) → choose reporting generation: `PYCHARM_BEHAVE_OLD_RUNNER` → null formatter + hook-based messages, else registered TeamCity formatter with base-dir-relative locations → resolve features (file / dir with *.feature / walk for `features` folder capped at 5000 children) → dry-run census with rollback → real `_RunnerWrapper.run()` → Django projects route through `_jb_django_behave.run_as_django_behave` first.
**Invariant:** The dry run must leave NO interpreter state behind except C-extension registrations (reimporting those raises "type already registered" via pybind11-style registries); step decorators live only in pure-Python modules so dropping them is safe.
**Probe:** executed 2026-08-25 — PASS: `len(set(buffer))`-style empty guard N/A here; verified `dry_run = True`, `_EXT_SUFFIXES` skip branch, `clean()` call, outline→scenarios expansion, null-vs-teamcity formatter registration names, 5000-children walk cap.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "behave dry_run features runner wrapper", limit: 10 });
// -> helpers/pydev+pycharm behave plane; decisive file plugins/python-ce/helpers/pycharm/behave_runner.py — EXECUTED (whole-file read)
```

## Verdict
Adopt: two-phase dry-run/real-run with sys.modules rollback exempting extension modules; custom formatter registration as the reporting seam; hook merge order user-before for before_* and custom-before-user for after_*. Adapt formatter registry name and env keys. Omit imp.get_suffixes py2 fallback.
