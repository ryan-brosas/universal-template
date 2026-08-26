<!-- capsule-v2 -->
# mypy `create_model` dynamic-class hook — how does a runtime factory call become a first-class type for the checker?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** How is the base class resolved from `__base__` (including type[Self] cases), and what nested-function quirk needs the extra symbol-table node?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/mypy.py:PydanticPlugin._pydantic_create_model_callback` (:190-232).
**Signature:** hook registered via `get_dynamic_class_hook` for fullname `pydantic.main.create_model`.
**Data Shape:** Produces `TypeInfo` via `ctx.api.basic_new_typeinfo(name, base_instance, line)` + `add_symbol_table_node`; inherits `base_info.metaclass_type`.

### Decisive source
```python
base_fullname = BASEMODEL_FULLNAME
for arg_name, arg_expr in zip(ctx.call.arg_names, ctx.call.args, strict=True):
    if arg_name == '__base__' and isinstance(arg_expr, RefExpr) and arg_expr.node is not None:
        if isinstance(arg_expr.node, TypeInfo):
            base_fullname = arg_expr.node.fullname
        elif isinstance(arg_expr.node, Var):
            arg_type = get_proper_type(arg_expr.node.type)
            if isinstance(arg_type, Instance):
                base_fullname = arg_type.type.fullname
            elif isinstance(arg_type, TypeType):
                item_type = get_proper_type(arg_type.item)
                if isinstance(item_type, TypeVarType):
                    # Inside classmethods, `cls` is modeled as `type[Self]`. Creating a concrete
                    # synthetic type here loses that type variable ... let mypy infer from the overload:
                    return
                if isinstance(item_type, Instance):
                    base_fullname = item_type.type.fullname

info = ctx.api.basic_new_typeinfo(ctx.name, base_instance, ctx.call.line)
info.metaclass_type = base_info.metaclass_type
ctx.api.add_symbol_table_node(ctx.name, SymbolTableNode(MDEF, info))

# Mypy has a quirk for serialization of classes nested in functions. This is a workaround:
if '@' in info.fullname:
    _, name = info.fullname.rsplit('.', maxsplit=1)
    ctx.api.modules[ctx.api.cur_mod_id].names[name] = SymbolTableNode(GDEF, info)
```

**Flow:** scan call args for `__base__` → resolve to TypeInfo through three shapes (direct TypeInfo / Var typed Instance / Var typed type[X] with TypeVar escape hatch) → fall back to BaseModel when unresolvable → mint the new TypeInfo filled with base's typevars, copy metaclass type, register in current module scope → if the synthesized fullname contains `'@'` (function-local class marker), ALSO publish under the bare name at module level so serialization finds it.
**Invariant:** The TypeVar early-return must bail BEFORE any symbol is added — otherwise a bogus concrete type shadows the correct overload inference. Metaclass propagation is explicit; basic_new_typeinfo does NOT inherit it.
**Probe:** `grep -n "'@' in info.fullname" pydantic/mypy.py` (:230 — the nested-class quirk branch).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "create_model dynamic class hook base", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-shape base resolution + metaclass copy + local-class republish; adapt names to your factory API; omit pydantic-settings interplay.
