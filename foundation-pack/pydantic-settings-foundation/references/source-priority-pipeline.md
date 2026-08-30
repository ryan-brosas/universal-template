<!-- capsule-v2 -->
# Source-priority fold — how does the pipeline guarantee "earlier source wins" without reversing the tuple?

**Source:** pydantic-settings MIT `main@d26fc0c3944fe68cf169f86386988bb83e3df2d8`; Codebase Memory `pydantic-settings`. **Question:** A porter must reproduce init > env > dotenv > secrets > defaults precedence exactly — where does the ordering live, and which side of the merge wins?

## Connected graph-selected seam
**Path/Symbol:** `pydantic_settings/main.py:_settings_build_values` (499-535), `_settings_init_sources` (300-496), `sources/base.py:DefaultSettingsSource` (262-307).
**Signature:** `(cls, sources: tuple[PydanticBaseSettingsSource, ...], init_kwargs: dict[str, Any]) -> dict[str, Any]`
**Data Shape:** ordered source tuple (first = highest priority); each `__call__` returns a flat/nested dict of field-key → value; output is one merged dict passed as `**kwargs` to normal pydantic validation.

### Decisive source
```python
states[source_name] = source_state
state = deep_update(source_state, state)
...
# Strip any default values not explicitly set before returning final state
state = {key: val for key, val in state.items() if key not in defaults or defaults[key] != val}
...
sources = cls.settings_customise_sources(...) + (default_settings,)
```

**Flow:** `_settings_init_sources` resolves every `_kwarg` override against `model_config`, builds Default→Init→Env→DotEnv→Secrets sharing one `InitState`, then appends `default_settings` AFTER whatever `settings_customise_sources` returns. The fold walks the tuple front-to-back merging `deep_update(new_source_state, accumulated)` — because the new state is the *first* argument, earlier sources overwrite later ones at every nesting level (`deep_update` recurses into dicts only; lists/scalars replace). Finally, keys whose value equals the `DefaultSettingsSource` snapshot are dropped so pydantic's own field defaults apply, and `_settings_restore_init_kwarg_names` re-keys entries back to the original init-kwarg spelling (alias-preferred) before `super().__init__(**state)`.
**Invariant:** Tuple order is the entire priority contract: position 0 must survive to the final value for every key it provides; no source may observe or mutate another's returned dict except through the read-only `current_state` view. An empty customizer tuple yields `{}` by design (`test_customise_sources_empty`), never an error.
**Probe:** `python3 -m pytest tests/test_settings.py -k test_merge_dict -p no:cacheprovider -q` — EXECUTED PASSING (`1 passed`) against checkout `main@d26fc0c3`; pins deep-merge across init+env: env JSON fills keys around an init-provided dict instead of replacing it.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-settings", query: "settings build values sources priority", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fold shape (`deep_update(source, acc)` + defaults-appended-last + default-equality strip) — it is host-independent. Adapt `deep_update` (it is imported from `pydantic._internal._utils`, not defined here — you must vendor or reimplement recursive-dict-merge) and the alias re-keying step if your model layer lacks validation aliases. Omit the CLI-source prepending branch unless porting the CLI plane.
