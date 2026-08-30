<!-- capsule-v2 -->
# MethodChecker name-resolution machine — AST-walk "is this method self-contained?" with three documented blind spots

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory project `smolagents`. **Question:** How does smolagents statically prove a Tool method only uses defined names, and where exactly does that proof not hold?

## Path/Symbol
- `src/smolagents/tool_validation.py:MethodChecker` (:11-154); `_BUILTIN_NAMES = set(vars(builtins))` (:8); allowlist imports `BASE_BUILTIN_MODULES` from `.utils` (same module list the sandbox import-authorization tree grants).

## Signature
`MethodChecker(class_attributes: set[str], check_imports: bool = True)`; `.visit(node)` appends human-readable strings to `.errors`.

## Data Shape
TEN-set Load-name allowlist: builtins vars, BASE_BUILTIN_MODULES, arg_names (incl. *args/**kwargs), `"self"`, class_attributes, imports (asname→name map), from_imports (asname→(module,name)), assigned_names, typing_names (`{"Any"}`), defined_classes.

### Decisive source
```python
# tool_validation.py:124-138 — the single gate
def visit_Name(self, node):
    if isinstance(node.ctx, ast.Load):        # stores/annotations never checked
        if not (node.id in _BUILTIN_NAMES or node.id in BASE_BUILTIN_MODULES
                or node.id in self.arg_names or node.id == "self"
                or node.id in self.class_attributes or node.id in self.imports
                or node.id in self.from_imports or node.id in self.assigned_names
                or node.id in self.typing_names or node.id in self.defined_classes):
            self.errors.append(f"Name '{node.id}' is undefined.")
# :115-117 — self.X subtree skipped wholesale
def visit_Attribute(self, node):
    if not (isinstance(node.value, ast.Name) and node.value.id == "self"):
        self.generic_visit(node)
```

## Flow
assigned_names is accumulated by dedicated visitors for plain Assign (incl. tuple/list unpacking), With-as, ExceptHandler-as, AnnAssign, For targets (Name or Tuple), and ALL THREE comprehension forms via one shared generator helper (:90-113) — so scoping is FLAT per method, not block-scoped like Python. A FRESH MethodChecker is built per FunctionDef by `validate_tool_attributes` (:255-259), seeded with class-level attributes. Imports do not error; they merely whitelist their bound names.

## Invariant
Three confirmed asymmetries (whole-file read at pin): (1) **`check_imports` is stored but NEVER consulted** (:18,:26 are its only occurrences) and `self.undefined_names` (:19) likewise dead — despite the docstring promising "no local imports", ANY import (local module included) passes; import enforcement lives nowhere else. (2) **`visit_Call` (:140-154) duplicates the allowlist but OMITS typing_names** — `x = Any()` errors while bare `Any` doesn't. (3) **`self.anything` is unverified** — attribute reads/writes through self bypass the walk entirely. Porters treating this as a security boundary will be wrong: it is a serialization-fidelity heuristic for source regeneration.

## Probe
`tests/test_tool_validation.py`: TestMethodChecker.test_multiple_assignments (:179-189) pins tuple-unpack tolerance; InvalidToolUndefinedNames.forward returns module-global `UNDEFINED_VARIABLE` → "Name 'UNDEFINED_VARIABLE' is undefined." expected via parametrized table (:123-141); default-tools smoke (:20-24). Live probe: run MethodChecker over `def f(self):\n import local_module\n return local_module.x` → errors == [] (no import rejection).

## Get live surrounding code
**Retrieve (executed 2026-08-26, project `smolagents`):**
```ts
await mcp.codebase_memory.search_graph({ project: "smolagents", query: "MethodChecker ast tool validation signature arguments checks", limit: 15 });
// 15/15 rows = MethodChecker visitors :18-154 exactly (visit_arguments/__init__/Import/Assign/With/For/Attribute/Name/Call/ImportFrom/ExceptHandler/AnnAssign/ListComp/DictComp/SetComp)
```

## Verdict
Adopt the collector-per-statement-form + flat-scope allowlist pattern for "will this source regenerate and re-import cleanly" checks. Adapt the sets to your host's stdlib list. Omit any claim of import hygiene or security — replicate smolagents' actual semantics, docstring notwithstanding.
