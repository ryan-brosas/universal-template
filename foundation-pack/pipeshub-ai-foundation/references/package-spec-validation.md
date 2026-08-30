<!-- capsule-v2 -->
# Package-spec validation + canonical keys — how are npm/PyPI specs made safe for argv and allowlists made spelling-tolerant?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How do you stop shell-metacharacter/`-flag` smuggling in package installs while letting `Pillow` vs `pillow` vs `python_docx` compare equal on allow/denylists?

## Reject-outside-charset regexes + PEP 503 canonicalization
**Path/Symbol:** `backend/python/app/agent_loop_lib/sandbox/coding/validation.py:validate_package_spec/package_name/canonical_package_key/matches_package_set` (L33–86).
**Signature:** `validate_package_spec(spec, language) -> bool`; `package_name(spec, language) -> str`; `canonical_package_key(name, language) -> str`; `matches_package_set(name, package_set, language) -> bool`.
**Data Shape:** npm: `[a-z0-9][a-z0-9._-]*` (+ optional `@range`, scoped `@org/pkg` form); PyPI: `[A-Za-z0-9][A-Za-z0-9._-]*` + optional comparator version. Anything else — whitespace, `git+`, `file:`, URLs, leading `-flag` — FAILS rather than being escaped.

### Decisive source
```python
def canonical_package_key(name, language):
    key = name.lower()
    if language != "typescript":
        key = key.replace("_", "-")   # PEP 503: python_docx == python-docx
    return key
    # npm names keep underscores — they're SIGNIFICANT there; only case folds.

def matches_package_set(name, package_set, language):
    if name in package_set:
        return True
    key = canonical_package_key(name, language)
    # BOTH directions normalized — a non-canonical ENTRY ('Pillow') in the
    # configured list still matches its canonical query name:
    return any(canonical_package_key(entry, language) == key for entry in package_set)
```

**Flow:** every backend (`LocalCodingSandbox` via EnvironmentManager, `DockerCodingSandbox.install_packages`, `E2BCodingSandbox.install_packages`) runs the identical ladder per spec: `validate_package_spec` (fail-closed `InstallResult`) → denylist `matches_package_set` → allowlist (if configured) → `canonical_package_key not in self._installed[language]` idempotency check → install.
**Invariant:** (1) Validation is fail-closed on ANY character outside the charset — metacharacters are never escaped or interpreted. (2) Membership checks must canonicalize BOTH the queried name AND the configured entries, or an exact-string list rejects specs the installer itself accepts. (3) The installed-set idempotency check uses canonical keys too, or `lodash@4.17.21` after `LODASH` re-installs forever. (4) This is the DEEP syntactic layer; the cheaper URL/`git+`/`file:` PRE_TOOL_USE middleware denylist upstream complements but does not replace it.
**Probe:** `tests/unit/agent_loop_lib/sandbox/test_validation.py::test_python_underscore_to_hyphen` (:27), `::test_npm_lowercases_but_keeps_underscores` (:30), `::test_non_canonical_allowlist_entries_match_canonical_name` (:47), `::test_versioned_capitalized_spec_matches_allowlist` (:66); end-to-end through backends: `test_local_coding_sandbox.py` :87–115 (`test_capitalized_spec_passes_backend_allowlist`, `test_second_install_with_different_casing_is_skipped`, `test_denylist_matches_canonically`), `test_docker_coding_sandbox.py:451–491`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "validate_package_spec canonical_package_key matches_package_set package_name", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the regex set + bidirectional canonicalization verbatim (it's ecosystem semantics, not style); adapt charsets if the host supports extra ecosystems. Omit PipesHub's curated-allowlist contents. Direct tests cover normalization, membership, and backend integration at HEAD.
