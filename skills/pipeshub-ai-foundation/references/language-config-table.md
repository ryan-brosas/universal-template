<!-- capsule-v2 -->
# Grammar-diff config table — how do you support 18 tree-sitter grammars with one walker, where adding a language is data instead of code?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** Which per-grammar quirks must a declarative LanguageConfig absorb so the generic engine never grows an `if language ==` branch — and what breaks silently when a node-type name is wrong?

## Frozen dataclass per language; every grammar disagreement is one field
**Path/Symbol:** `backend/python/app/modules/parsers/code_parser/lang_config.py:LanguageConfig/_ALL_CONFIGS` (L33–101 type, L110–459 the 18 configs, L462–503 registries; whole file 503L).
**Signature:** `LanguageConfig(name, ts_module, ts_language_fn, extensions, *, class_types=…12 definition sets…, decorator_wrapper_types, attached_types, trailing_body_types, import_types, export_types, binding_types, function_value_types, name_field="name", body_field="body", name_field_overrides={}, name_fallback_child_types=(…), body_fallback_child_types=(), unwrap_declarator=False, container_kinds, method_container_kinds, docstring_style, doc_line_prefixes)`; helpers `config_for_extension(ext)`, `config_for_language(name)`, `detect_language(file_name)`.
**Data Shape:** `_EXT_TO_CONFIG` built once at import by `_build_extension_index()`; `LANGUAGES: dict[name → cfg]`; `SUPPORTED_CODE_EXTENSIONS: frozenset`.

### Decisive source
```python
def _build_extension_index() -> dict[str, LanguageConfig]:
    """Two configs claiming one extension would resolve by dict order, silently
    routing a language to the wrong grammar."""
    for cfg in _ALL_CONFIGS:
        for ext in cfg.extensions:
            if ext in index:
                raise ValueError(
                    f"extension {ext!r} claimed by both {index[ext].name!r} and {cfg.name!r}")
```

**Flow:** Import-time extension index construction (duplicate claim = LOUD ValueError, never dict-order resolution) → `detect_language` rpartitions the file name and maps `.h` to the C++ grammar (superset; headers routinely hold C++, node types identical for the C subset) → walker consults only config fields. The fields encode each grammar's pathology: `decorator_wrapper_types` (Python `decorated_definition`, C++ `template_declaration`, Go `type_declaration`) lend their byte range so decorator text stays in the block; `attached_types` extend comments with Rust `attribute_item`/C#-PHP `attribute_list`; Dart's `trailing_body_types` re-unites signature + sibling body; JS-family `binding_types`+`function_value_types` recover `const handler = () => {}` as a named function; C-family `unwrap_declarator=True` digs names out of pointer/array/function declarator chains; Rust's single `name_field_overrides={"impl_item": "type"}`.
**Invariant:** (1) Adding a language is ONE entry + its grammar dependency — the walker never changes. (2) A missing comment node-type name turns doc comments into detached blocks instead of attachments (`COMMENT_NODE_TYPES` union is load-bearing). (3) Kotlin import node differs between grammar 1.1.0 (`import`) and older forks (`import_header`) — both listed. (4) `method_container_kinds ⊂ container_kinds`: namespaces/mods tile but do NOT promote functions to methods. (5) Swift folds class/struct/extension into one `class_declaration`; Go's `type Foo struct{}` needs the wrapper-to-spec trick (`struct_types={type_spec}` + `decorator_wrapper_types={type_declaration}`). (6) Name resolution ladder order: name-field (with overrides) → declarator chain (if enabled) → fallback child types → one level down into a wrapped signature child (Dart `method_signature`→`function_signature`).
**Probe:** `test_exhaustiveness.py::test_every_configured_grammar_loads` (:122–134) pins ABI drift at test time ("a grammar wheel compiled against a different tree-sitter ABI fails at Language() construction … rather than on the first file of that language in production"); `test_every_language_finds_at_least_one_named_definition` (:103) catches simply-wrong node-type sets; duplicate-extension ValueError has no dedicated test (import-time failure — any regression breaks every collection).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project mnt-hdd-utopia-inspo-platforms-pipeshub-ai --query "LanguageConfig detect_language" --detail ids
```

## Verdict
Adopt the pattern wholesale for any multi-language parser: frozen dataclass table + loud import-time collision check + walker that reads config only. Adapt the node-type vocab to your pinned grammar versions (they drift across major versions — the Kotlin import split proves it). Omit nothing if you keep all 18 languages; dropping languages means pruning their configs, not adding branches. Coverage caveat: per-config quirk correctness is exercised through the tiling suite's per-language samples, not unit tests of individual fields.
