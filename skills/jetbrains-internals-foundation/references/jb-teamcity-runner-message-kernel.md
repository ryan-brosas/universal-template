<!-- capsule-v2 -->
# jb TeamCity runner message kernel — how do N test-runner adapters share one node-id tree protocol?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214; Codebase Memory project `jetbrains-pycharm`. **Question:** How can every Python test runner emit IDE-navigable hierarchical results without each adapter reimplementing tree bookkeeping?

## Monkeypatch the TC client once; enrich every message with nodeId/parentNodeId/locationHint
**Path/Symbol:** `plugins/python-ce/helpers/pycharm/_jb_runner_tools.py`:100-175 `NewTeamcityServiceMessages`; :319 monkeypatch assignment; :61-84 socket transport; :303-316 `close_suites`; :369-389 `jb_start_tests`/`start_protocol`.
**Signature:** `message(self, messageName, **properties)` (overrides `TeamcityServiceMessages.message`); `jb_patch_targets(targets, fs_glue, old_python_glue, new_python_glue, fs_to_python_glue)`.
**Data Shape:** `_test_suites: OrderedDict[full_name → TestSuiteInfo(full_name,node_id,parent_node_id,is_test,was_stopped)]`; tree ids from Serial/ParallelTreeManager (`JB_USE_PARALLEL_TREE_MANAGER`, root offset via `--offset`).

### Decisive source
```python
messages.TeamcityServiceMessages = NewTeamcityServiceMessages   # the WHOLE kernel is this patch
...
def message(self, messageName, **properties):
    if messageName in {"enteredTheMatrix", "testCount"}:
        if "_jb_do_not_call_enter_matrix" not in os.environ:
            _old_service_messages.message(self, messageName, **properties)
        return
    ...
    properties["locationHint"] = "python<{0}>://{1}".format(PROJECT_DIR, possible_location)
    # data-driven tests instead:  locationHint = "file:/"+path+":"+lineno   (docstring "(...)" stripped)
    current, parent = _TREE_MANAGER_HOLDER.manager.get_node_ids(full_name)
    if not current and not parent: return          # outside requested subtree → swallow
    properties["name"] = str(full_name).split(".")[-1]     # short-name shortcut
    properties["nodeId"] = str(current); properties["parentNodeId"] = str(parent)
```
Transport: one shared socket — `JB_TEAMCITY_SOCKET_PATH` (AF_UNIX) wins over `JB_TEAMCITY_SOCKET_HOST/PORT` (AF_INET); `_SocketTeamCityMessagesPrinter.sendall`s raw messages to preserve order.

**Flow:** import time patches the TC library globally → any runner using teamcity-messages transparently gains node ids → `jb_start_tests` = parse args (`--path/--target/--offset`, `--` passthrough), restore sys.path (helpers dir popped from front), emit `enteredTheMatrix` → per-test messages enriched and recorded in `_test_suites` → `testIgnored(stopped=true)` marks ancestor chain stopped → `jb_finish_tests` → `close_suites()`: reversed-order failsafe emitting `testIgnored(stopped)` for unfinished tests and `testSuiteFinished` for the rest.
**Invariant:** Enrichment must be invisible to plain TeamCity consumers (only additive attributes + name-shortcut). The exit-time failsafe guarantees no suite/test is left open even when the underlying runner crashes mid-run.
**Probe:** executed 2026-08-25 — PASS: monkeypatch assignment verbatim; AF_UNIX env checked before AF_INET; `_jb_do_not_call_enter_matrix` suppression gate; both locationHint schemes present; `close_suites` defined.

## Get live surrounding code
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-pycharm", qualified_name: "jetbrains-pycharm.plugins.python-ce.helpers.pycharm._jb_runner_tools.NewTeamcityServiceMessages.message" });
// -> start_line 121 end_line 175 — EXECUTED
```

## Verdict
Adopt: single-point library monkeypatch as the integration seam; additive nodeId/parentNodeId/locationHint enrichment; ordered socket transport; reversed-order close failsafe. Adapt the tree-id allocator (serial vs parallel manager) and suppression env names. Omit py2 `map` returns and setup/teardown block hacks (upstream issue #114).
