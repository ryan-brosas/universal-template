<!-- capsule-v2 -->
# pydevd namespace extension API — third-party resolvers/renderers without forking the debugger?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214 (non-git; freshness = product-info.json buildNumber re-read unchanged); Codebase Memory project `jetbrains-pycharm` (full mode, 103533 nodes). **Question:** What must an out-of-tree extension look like to be picked up by the running debugger?

## pkgutil.extend_path preamble + pydevd_plugin* module-name prefix + ABC registration
**Path/Symbol:** `plugins/python-ce/helpers/pydev/pydevd_plugins/extensions/README.md` (whole contract); ABCs in `_pydevd_bundle/pydevd_extension_api.py`:18-47 `_AbstractResolver`, :50-53 `_AbstractProvider`.
**Signature:** the two `__init__.py` files carry ONLY this preamble:
**Data Shape:** drop a python-path root containing `pydevd_plugins/extensions/pydevd_plugin_<name>.py`; namespace merge lets BOTH the shipped tree and your tree answer for the same package name.

```python
import pkgutil
__path__ = pkgutil.extend_path(__path__, __name__)
```

### Decisive source
README rules: "1. Ensure that the root folder of your extension is in sys.path ... 4. Your plugin name inside the extensions folder must start with pydevd_plugin 5. Implement one or more of the abstract base classes defined in _pydevd_bundle.pydevd_extension_api, this can be done by either inheriting from them or registering with the abstract base class".

**Flow:** PYTHONPATH merge makes the extension's `pydevd_plugins.extensions` package SHARE the namespace with the shipped one (extend_path appends search paths instead of shadowing) → modules named `pydevd_plugin*` are discovered → classes registered against the ABCs (inheritance or register()) are invoked from the variable/table rendering pipeline (`pydevd_resolver.py`, `pydevd_tables.py`, `pydevd_user_type_renderers.py`).
**Invariant:** The name prefix IS the discovery key, and the preamble-only rule prevents accidental package shadowing; breaking either silently removes extensions rather than erroring.
**Probe:** executed 2026-08-25 — PASS pkgutil.extend_path preamble (exact two-line match), PASS pydevd_plugin name prefix rule.
**Coverage caveat:** README.md is not symbol-indexed; evidence = direct read; code side corroborated by graph retrieval of the ABC classes (below).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-pycharm", query: "pydevd_extension_api abstract base class register type rewriter", limit: 5 });
// -> _AbstractResolver @ _pydevd_bundle/pydevd_extension_api.py:18-47, _AbstractProvider :50-53 — EXECUTED
```

## Verdict
Adopt namespace-package extension loading (preamble + prefix + ABCs) as the safest in-process plugin mechanism. Adapt the ABC surface to your renderer needs. Omit setuptools entry-point alternatives — pydevd deliberately uses explicit namespace packages.