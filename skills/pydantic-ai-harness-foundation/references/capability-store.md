<!-- capsule-v2 -->
# CapabilityStore — disk-backed runtime-authored capabilities with atomic manifest upsert and fail-soft loading

**Source:** pydantic-ai-harness (MIT) `main@c79fabc58fd3bd587dcc27f9e7d9de179d748cf0`; Codebase Memory `pydantic-ai-harness`. **Question:** how does a harness persist capabilities authored at runtime as `<name>.py` files plus a manifest index, with crash-safe writes and validation that never leaks `Any`?

## CapabilityStore + validation
**Path/Symbol:** `pydantic_ai_harness/capability_creation/_store.py` — `CapabilityStore`, `AuthoredCapability`, `_Manifest`; `_validate.py` — `load_capability_instance`, `validate_capability_file`, `CapabilityValidationError`, `_load_module`, `_is_capability_subclass`, `_check_model_settings_return`; `_capability.py`, `_toolset.py`.
**Signature:** `CapabilityStore(directory: Path)`; `write(name, code) -> AuthoredCapability`; manifest entry `AuthoredCapability(name, module_file, class_name, status='active'|'disabled', last_error=None)`.
**Data Shape:** each authored capability is one `<name>.py` under `directory`; a sibling `manifest.json` indexes them (name, module file, class, status, last validation error) and is the surface a UI can read. Name regex `^[a-z][a-z0-9_]*$`.

### Decisive source
```python
# _save_manifest: write to a temp file in the same directory, then atomically
# replace the manifest, so a crash mid-write never leaves a partial/corrupt
# file that _load_manifest would read as "no capabilities".
# _load_manifest: fail-soft -- on (OSError, ValidationError, ValueError) return
# an empty _Manifest(), skipping corrupt entries rather than raising.
# _load_module: import path as a FRESH module not registered in sys.modules, and
# suppress the on-disk bytecode cache, so re-authoring under the same name
# always re-executes the new source.
# _is_capability_subclass / _check_model_settings_return: every value crossing
# back from dynamically-imported code is narrowed with isinstance/issubclass or
# type-checked, so nothing typed Any escapes the module.
```

**Flow:** `write(name, code)` → validate/import fresh module → construct instance → write `<name>.py` → atomic upsert manifest → return entry. `_upsert` is a read-modify-write keyed by name.
**Invariant:** crash-safe manifest (temp+atomic replace); fail-soft load never raises on corrupt entries; re-authoring under the same name always re-executes fresh source; dynamic-import boundary never leaks `Any`.
**Probe:** `tests/capability_creation/test_capability_creation.py` pins write/validate/upsert, re-authoring, and manifest round-trip.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "CapabilityStore write _save_manifest _load_module validate_capability_file", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt atomic manifest upsert, fail-soft loading, fresh-module re-import, and the no-`Any` boundary; adapt the name regex and validation rules; omit host-specific capability wiring.
