<!-- capsule-v2 -->
# Language disambiguation — when three languages share one extension, who wins?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you resolve `.m` (ObjC/Magma/MATLAB), `.cls` (Apex/ObjectScript), `.inc` without a content peek on every file?

## Content-sniff only for ambiguous extensions, deterministic defaults
**Path/Symbol:** `src/discover/discover.c:cbm_disambiguate_m/_cls/_inc` + shebang fallback; tests in tests/test_language.c:566–612 (`lang_m_objc/magma/matlab/default_on_read_fail`), `lang_fn_blade_php_compound_issue258`.
**Signature:** `CBMLanguage cbm_disambiguate_m(const char *path);` (+ `_cls`, `_inc` twins)
**Data Shape:** Reads at most the FIRST 4KB. `.m`: `#import`/`#include`/`@interface`-style markers ⇒ OBJC; MATLAB-specific constructs ⇒ MAGMA vs MATLAB ordering per marker table; read failure ⇒ CBM_LANG_MATLAB (deterministic default). `.cls`: first line matching `Class <Uppercase>` ⇒ OBJECTSCRIPT_UDL else APEX. `.inc`: ROUTINE header ⇒ OBJECTSCRIPT_ROUTINE else BITBAKE.

### Decisive source
```c
/* Disambiguate .m files by reading first 4KB of content.
 * Returns CBM_LANG_OBJC, CBM_LANG_MAGMA, or CBM_LANG_MATLAB.
 * On read failure, defaults to CBM_LANG_MATLAB. */
```
```c
/* Detect a supported script language from a file's shebang (#1...) first line.
 * Conservative fallback used ONLY when filename/extension detection is unknown;
 * it never overrides extension or special-filename [matches]. */
```

**Flow:** filename special-cases (Makefile, CMakeLists.txt, …) → extension table → ambiguous-extension sniffers → unknown-extension user config (`extra_extensions`, project beats global) → shebang as last resort → CBM_LANG_COUNT.
**Invariant:** Sniffers never override unambiguous matches; every ambiguity must end in ONE deterministic language even on I/O failure, so incremental runs stay stable.
**Probe:** `tests/test_language.c:lang_m_objc`, `lang_m_magma`, `lang_m_default_on_read_fail`, `lang_fn_blade_php_compound_issue258`; registry stability via `tests/test_registry.c`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_disambiguate_m", limit: 5 });
```

## Verdict
Adopt ordered resolution ending in deterministic defaults; adapt the marker tables to your languages; omit vendored grammar registration details unless adding a new language.
