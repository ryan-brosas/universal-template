<!-- capsule-v2 -->
# Model settings splice — how do user-supplied settings override a module-global table without rebinding it?

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How can late-loaded YAML settings replace entries in an already-imported module constant so that every existing importer sees the update — and how does one magic name become a global overlay?

## Slice assignment replaces by name while preserving list identity
**Path/Symbol:** `aider/models.py`: `register_models` (:1085-1109), `sanity_check_models` (:1146-1161), `sanity_check_model` (:1164-1200); direct test anchor `tests/basic/test_models.py::test_aider_extra_model_settings` (:374-423).
**Signature:** `register_models(model_settings_fnames) -> list[str]` (files actually loaded); `sanity_check_models(io, main_model) -> bool`.
**Data Shape:** YAML file → list of dicts → `ModelSettings(**dict)` dataclasses; module global `MODEL_SETTINGS: list[ModelSettings]`.

### Decisive source
```python
for model_settings_dict in model_settings_list:
    model_settings = ModelSettings(**model_settings_dict)
    # Remove all existing settings for this model name
    MODEL_SETTINGS[:] = [ms for ms in MODEL_SETTINGS if ms.name != model_settings.name]
    # Add the new settings
    MODEL_SETTINGS.append(model_settings)
```
```python
# test_models.py :374 — the "aider/extra_params" wildcard entry:
# register name="aider/extra_params", then EVERY Model merges its extra_params
model = Model("claude-3-5-sonnet-20240620")
self.assertEqual(model.extra_params["extra_headers"]["Foo"], "bar")          # user key wins
self.assertEqual(model.extra_params["extra_headers"]["anthropic-beta"],
                 ANTHROPIC_BETA_HEADER)                                      # default survives
```

**Flow:** missing files are skipped silently; blank files skipped; parse errors re-raised wrapped with the filename. Replace-by-name uses slice assignment (`MODEL_SETTINGS[:] = ...`) so the list OBJECT keeps its identity — any module that did `from aider.models import MODEL_SETTINGS` before registration still observes the change. The special name `"aider/extra_params"` is never matched as a model; Model construction deep-merges its extra_params UNDER each model's own (per-subdict merge: user keys added, provider defaults like max_tokens win for shared keys).
**Invariant:** settings registration must not rebind the module global, or pre-import consumers silently keep stale defaults; sanity warnings must cover exactly three roles with identity dedup (weak checked only if `is not main_model`; editor only if distinct from BOTH main and weak).
**Probe:** direct tests executed this pass: `.venv/bin/python -m pytest tests/basic/test_models.py -k 'extra or sanity or register' -q` → **passed** (subset of the 6-passed run incl. test_aider_extra_model_settings :374, test_sanity_check_models_bogus_editor :83). Anchor: DSH grep `MODEL_SETTINGS\[:\]` on aider/models.py → **exactly 1 match at :1102**.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "register_models", limit: 10 });
// rank-2: aider.aider.models.register_models aider/models.py 1085-1109 (main.py twin rank-1; sanity_check_models :1146-1161 rank-3)
```

## Verdict
Adopt slice-splice replacement for mutable registries consumed via from-imports, and the named-wildcard overlay pattern for cross-cutting request params. Adapt the merge depth to your config schema (aider merges two levels). Omit the fuzzy-match suggestions in `sanity_check_model` unless your CLI has a comparable model catalog.
