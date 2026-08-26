<!-- capsule-v2 -->
# should import boundary — when is a dependency emitted as an import versus inlined as source?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** Given a dependency's module path, how do I decide "emit `import x`" vs "inline x's source into the closure"?

## origin-path classification (and the two-implementations trap)
**Path/Symbol:** `src/ell/util/should_import.py:should_import` (:9-79) — the one imported by `closure.py`; legacy variant at `src/ell/util/closure_util.py:should_import` (:129-153) — cwd-prefix based, still exported; tests target the modern one.
**Signature:** `should_import(module_name: str, raise_on_error: bool = False) -> bool`.
**Data Shape:** inputs are module names; decision inputs are resolved spec origins vs site-packages paths, sys.path entries, stdlib dir, and `ELL_PROJECT_ROOT`.

### Decisive source
```python
# should_import.py:20-21 — ell itself is ALWAYS importable, never inlined
if module_name.startswith("ell"):
    return True
...
# should_import.py:52-66 — the classification core
for pkg in site_packages_paths:
    if origin_path.is_relative_to(pkg):
        return True

for path in additional_paths:
    if origin_path.is_relative_to(path):
        return False

for local in local_paths:
    if origin_path.is_relative_to(local):
        return False

return True
```

**Flow:** find_spec → no spec or no origin ⇒ False (namespace/odd modules inline). Then order matters: site-packages (incl. stdlib appended to the same list) ⇒ True first; other sys.path entries minus site-packages ⇒ False; project root (`ELL_PROJECT_ROOT` env or cwd) ⇒ False. Any exception returns True by default (`raise_on_error=False`) — fail-open toward import lines so a weird module never kills closure generation. The legacy `closure_util` twin checks `spec.origin.startswith(DIRECTORY_TO_WATCH)` string-prefix style and is what older code paths import; both agree on the ell-prefix short-circuit.
**Invariant:** the framework's own namespace must always classify as importable (inlining ell into every stored version would be absurd); and anything resolvable inside the user's project is *code under version control* → inline it, because an import line cannot pin its content.
**Probe:** `tests/test_should_import.py:test_should_import_ell_prefix` (:223-246) pins `"ell.local_module"` with local origin ⇒ True (prefix wins over locality); `test_should_import_standard_library` (:283-) and `test_should_import_local_module` (:310-) pin stdlib=True / local=False on the modern implementation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "immutable variable state", limit: 5, fields: ["signature", "name", "file"] });
// adjacent serialization seam; boundary seam resolves via test anchors:
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "should import exception handling", limit: 3, fields: ["name", "file"] });
// rank-1: ext-ell.tests.test_should_import.test_should_import_exception_handling @ tests/test_should_import.py:122
```

## Verdict
Adopt origin-path-based classification with the ell-style self-namespace short-circuit. Adapt path lists to your packaging layout (editable installs blur site-packages — resolve() everything first, as upstream does). Omit nothing silently: if you keep only ONE implementation, delete the other file, because divergent twins here produce version hashes that differ by import strategy.
