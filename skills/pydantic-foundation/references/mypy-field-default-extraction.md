<!-- capsule-v2 -->
# Field-default/alias/strict extraction from `Field(...)` call ASTs — how does the plugin read defaults without evaluating expressions?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** What are the exact syntactic rules for `has_default`, alias presence, and per-field strict from an AssignmentStmt?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/mypy.py:get_has_default` (:1084-1104), `get_alias_info` (:1122-1150), `get_strict` (:1106-1120).
**Signature:** static methods over `stmt: AssignmentStmt` whose rvalue is (usually) a CallExpr to `pydantic.fields.Field`.
**Data Shape:** `get_has_default -> bool`; `get_alias_info -> tuple[str | None, bool]` where the bool `has_dynamic_alias` excludes string literals; `get_strict -> bool | None`.

### Decisive source
```python
# has_default: TempNode means annotation-only (no default). Inside a Field() call, the FIRST positional
# arg or explicit default= is the default unless it's `...`; default_factory= counts unless None:
for arg, name in zip(expr.args, expr.arg_names, strict=True):
    if name is None or name == 'default':
        return arg.__class__ is not EllipsisExpr
    if name == 'default_factory':
        return not (isinstance(arg, NameExpr) and arg.fullname == 'builtins.None')
return False
# outside a call: default exists iff rvalue is not bare Ellipsis
return not isinstance(expr, EllipsisExpr)

# alias: validation_alias takes precedence over alias; StrExpr → literal alias; anything else → dynamic:
if 'validation_alias' in expr.arg_names:
    arg = expr.args[expr.arg_names.index('validation_alias')]
elif 'alias' in expr.arg_names:
    arg = expr.args[expr.arg_names.index('alias')]
else:
    return None, False
if isinstance(arg, StrExpr):
    return arg.value, False
else:
    return None, True
```

**Flow:** inspect mypy AST nodes only — never evaluate. `TempNode` marks annotation-only declarations (`x: int` with no value). `EllipsisExpr` (`...`) means "required". Positional-arg detection relies on `arg_names[i] is None`.
**Invariant:** `x: Final = 42` arrives as a NON-new_syntax assignment with inferred type — handled separately via `analyze_simple_literal_type`. A dynamic alias (alias_generator or non-literal) makes the signature UNKNOWABLE: combined with `warn_required_dynamic_aliases` config it errors; in signatures it forces ARG_NAMED (never positional) and disables `use_alias` filtering.
**Probe:** `grep -n 'arg.__class__ is not EllipsisExpr' pydantic/mypy.py` (:1099) + `grep -n "expr.args\[expr.arg_names.index('validation_alias')\]" pydantic/mypy.py` (:1141).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "get_has_default get_alias_info Field assignment", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pure-AST extraction rules (identity checks against sentinel node types); adapt to your checker's AST; omit deprecated validator-call disambiguation.
