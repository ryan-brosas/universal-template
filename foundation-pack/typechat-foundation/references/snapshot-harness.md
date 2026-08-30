<!-- capsule-v2 -->
# Snapshot test harness — how do per-Python-version schema snapshots pin the compiler?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** How does the Python test suite snapshot generated TypeScript across interpreter versions, and what does a porter need to know to extend or adjudicate it?

## syrupy single-file extension
**Path/Symbol:** `python/tests/utilities.py:13-60` (`TypeScriptSchemaSnapshotExtension`, `PyVersionedTypeScriptSchemaSnapshotExtension`, `PyVersioned3_12_PlusSnapshotExtension`, `check_snapshot_for_module_string_if_3_12_plus`, `snapshot_schema` fixture).
**Signature:** extension serializes `TypeScriptSchemaConversionResult` to text: header `// Entry point is: '<typescript_type_reference>'`, optional `// ERRORS:` block with one `// !!! <error>` line each, then the raw schema; file extension `.schema.d.ts`.
**Data Shape:** snapshot dirs: default `__snapshots__/<test_name>/`, version-specific `__py3.11_snapshots__/`, `__py3.12_snapshots__/`, `__py3.14_snapshots__/`, and `__py3.12+_snapshots__/` for ≥3.12-only syntax (PEP 695 `type` statements).

### Decisive source
```py
def check_snapshot_for_module_string_if_3_12_plus(snapshot, input_type_str, module_str):
    if sys.version_info < (3, 12):
        pytest.skip("requires python 3.12 or higher")
    module = types.ModuleType("test_module")
    exec(module_str, module.__dict__)
    type_obj = eval(input_type_str, globals(), module.__dict__)
    assert(python_type_to_typescript_schema(type_obj) == snapshot(extension_class=PyVersioned3_12_PlusSnapshotExtension))
```
**Flow:** tests define types inline (or exec source strings for 3.12+ syntax) → convert → compare against checked-in `.schema.d.ts`.
**Invariant:** ERROR TEXT IS PART OF THE SNAPSHOT — the py3.11 conflicting-names snapshot predates a converter change and shows NO error banner while the py3.12 twin shows it; both pass because each runs only on its own interpreter. When adjudicating "stale" snapshots, run on the MATCHING interpreter before concluding drift. The 3.12+ harness deliberately uses exec/eval because PEP 695 type-alias syntax cannot be expressed portably in test modules.
**Probe:** full-suite live runs at pin 83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc on TWO CI-matrix interpreters: pass-1 /tmp/tc-p1-run (uv venv 3.12): `python -m pytest tests -q` → **22 passed, 17 snapshots passed**; this pass /tmp/tc-p3-run (`python3.14 -m venv` + `pip install -e 'python[dev]'`): repo-owned `pytest -vv` → **22 passed, 17 snapshots passed in 0.25s** (Python 3.14.7, pytest 8.4.2, syrupy 6.0.0). Identical counts across 3.12 and 3.14 confirm the versioned-dir split is complete for the tested surfaces; note the graph's python/tests File inventory lists only `.schema.d.ts` snapshots — the amber `test_translator.ambr` is a direct-read-only artifact.
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"snapshot_schema PyVersionedTypeScriptSchemaSnapshotExtension","limit":3}'
// utilities.py sits under python/tests (TESTS package node family in graph)
```

## Verdict
Adopt the versioned-snapshot pattern wholesale when porting any code-gen surface (it caught real cross-version behavior); adapt dir naming to your runner; omit exec/eval gymnastics only if your minimum floor already includes the syntax you test. Coverage caveat: none — this seam IS the test layer.
