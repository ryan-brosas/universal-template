<!-- capsule-v2 -->
# pydevd wire command vocabulary — how do debugger peers agree on command semantics without a schema?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214 (non-git; freshness = product-info.json buildNumber re-read unchanged); Codebase Memory project `jetbrains-pycharm` (full mode, 103533 nodes). **Question:** What is the stable contract when adding or consuming a pydevd debugger command?

## Integer command-code table + string meaning mirror
**Path/Symbol:** `plugins/python-ce/helpers/pydev/_pydevd_bundle/pydevd_comm_constants.py`:1-191 (`CMD_*` constants; `ID_TO_MEANING` at :111).
**Signature:** module constants — `CMD_RUN = 101` … `CMD_ERROR = 901`; `ID_TO_MEANING: dict[str, str]` (STRING keys).
**Data Shape:** ranges: 101-160 core debug loop; 170 unit-test mode; 190 user type renderers; 200-206 output/goto/dataviewer/console; 210-214 data-viewer/image chunks; 501 `CMD_VERSION`, 502 `CMD_RETURN`, 503 `CMD_SET_PROTOCOL`; 901 `CMD_ERROR`.

### Decisive source
```python
CMD_VERSION = 501
CMD_RETURN = 502
CMD_SET_PROTOCOL = 503
CMD_ERROR = 901

ID_TO_MEANING = {
    '101': 'CMD_RUN',
    ...
}
```

**Flow:** IDE writes `(id, seq, text)` frames → `ReaderThread.process_command` → `_pydevd_bundle/pydevd_process_net_command.py:process_net_command` (:77) big if/elif switch keyed on the raw ints (docstring records why: dict dispatch loses to if..elif below ~20-25 choices). Responses go back through `NetCommand` factories.
**Invariant:** The integer IDs are the protocol — never renumber shipped codes (the file itself carries a `# Note: renumbered (conflicted on merge)` scar). `ID_TO_MEANING` is a DIAGNOSTICS mirror, not dispatch truth, and may lag: probe measured exactly 75 `CMD_` constants vs mapping missing 3 codes (`CMD_SET_UNIT_TEST_DEBUGGING_MODE`=170, `CMD_IMAGE_COMMAND_START_LOAD`=213, `CMD_IMAGE_COMMAND_CHUNK_LOAD`=214), zero orphan meanings.
**Probe:** executed 2026-08-25 from install root — python3 regex battery: `PASS CMD_RUN==101 / CMD_VERSION==501 / CMD_ERROR==901 / ID_TO_MEANING['501']=='CMD_VERSION'`; diff printed `codes WITHOUT ID_TO_MEANING entry: [('170','CMD_SET_UNIT_TEST_DEBUGGING_MODE'),('213','CMD_IMAGE_COMMAND_START_LOAD'),('214','CMD_IMAGE_COMMAND_CHUNK_LOAD')]`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "process_net_command big switch main_lock", limit: 5 });
// -> jetbrains-pycharm.plugins.python-ce.helpers.pydev._pydevd_bundle.pydevd_process_net_command.process_net_command @ plugins/python-ce/helpers/pydev/_pydevd_bundle/pydevd_process_net_command.py:77 (Function) — EXECUTED
```

## Verdict
Adopt integer-id wire vocabulary + separate human-readable diagnostic mirror that is ALLOWED to lag (keeps hot path free of table maintenance). Adapt id ranges to your host's feature families. Omit Python-2 compat shims around the tables.