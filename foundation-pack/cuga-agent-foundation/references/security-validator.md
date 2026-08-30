<!-- capsule-v2 -->
# SecurityValidator — two-tier AST gate with a contextvar relaxation escape hatch

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** An agent executes LLM-generated Python in-process (no OS sandbox). How do you block dangerous imports/calls/attribute escapes while still letting skill flows import what they legitimately need — without a boolean flag smeared through every check?

## The validator
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/common/security.py` (`SecurityValidator` :101-379, `_SecurityAstVisitor` :12-98, `validate_imports` :226-250, `validate_wrapped_code` :308-323, `validate_dangerous_modules` :289-305, `is_relaxed_execution` from `benchmark_mode.py`).
**Signature:** `validate_imports(code)` (allowlist tier); `validate_wrapped_code(wrapped)` (strict AST tier); `validate_dangerous_modules(wrapped)` (light CodeAgent tier); all no-op under relaxed execution.
**Data Shape:** module sets: `DANGEROUS_IMPORTS`/`ALLOWED_IMPORTS` (import allowlist), `FORBIDDEN_MODULES` (strict: os/sys/subprocess/pathlib/shutil/glob/importlib + requests/socket/urllib/http/ctypes/pickle/marshal/shelve/pdb/builtins), `DANGEROUS_IMPORT_MODULES` (light 5-module subset), `FORBIDDEN_CALLS` (open/eval/exec/compile/__import__/setattr/delattr/hasattr/getattr/breakpoint), `FORBIDDEN_ATTRS` (env, f_locals, f_globals, f_back, f_code).

### Decisive source
```python
# security.py:238-239, 302-303, 320-321, 335-336, 350-351 — ONE escape hatch
if is_relaxed_execution():
    return   # every entry point checks the same contextvar first

# security.py:48-56 — attribute-level escape detection (strict only)
def visit_Attribute(self, node):
    if attr.startswith('__') and attr.endswith('__'): raise PermissionError(...)  # dunder
    if attr in self.forbidden_attrs:      raise PermissionError(...)             # frame escape
    root = self._root_name(node.value)    # os.path... -> root "os"
    if root in self.forbidden_modules:    raise PermissionError(...)
```

**Flow:** `validate_syntax` (compile with `PyCF_ALLOW_TOP_LEVEL_AWAIT`) runs UNCONDITIONALLY — it answers "will exec() parse this", not a security policy; then per tier: import allowlist (top-level module segment must be in ALLOWED_IMPORTS and not DANGEROUS) → strict wrapped-code AST walk (forbidden imports by Import/ImportFrom root segment, Name loads of forbidden modules, dunder + frame-escape attributes, forbidden calls incl. getattr/setattr which enable dynamic bypasses) → light tier for CodeAgent where LLM code may legitimately use dunders (only the 5 dangerous import modules checked). `filter_safe_locals` strips dangerous module names from injected locals; `assert_safe_globals` asserts os/sys/subprocess absent post-construction.
**Invariant:** syntax validation is policy-independent and never relaxes; ALL five security entry points consult the same contextvar (`set_skills_relaxed_execution` token set around a whole skills-enabled run), so relaxation is scoped and reversible rather than a config flag read at import time. Checks are AST-based so string literals (tool arguments containing "import os") never trigger false positives.

**Probe:** direct tests `executors/tests/test_security_validator.py` (whole file); `executors/tests/test_code_executor.py::test_syntax_error_blocked_before_exec_in_skills_relaxed_mode` (:378) — pins that SYNTAX still blocks under relaxation while security checks skip; `::test_skills_relaxed_skips_wrapped_code_validation` (:441), `::test_wrapped_code_validation_active_without_skills` (:449).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "SecurityValidator validate_wrapped_code FORBIDDEN_MODULES _SecurityAstVisitor is_relaxed_execution", limit: 10 });
```

## Verdict
Adopt the tiered strictness (interactive strict / CodeAgent light / syntax always), the single contextvar relaxation token for skill flows, and AST-only pattern matching (never regex over raw text). Adapt the module/call/attr lists to your runtime's attack surface — treat getattr/setattr/frame-access as forbidden since they enable dynamic bypasses. Omit the AppWorld benchmark unrestricted-globals mode unless reproducing evals.
