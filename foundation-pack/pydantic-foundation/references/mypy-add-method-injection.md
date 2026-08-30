<!-- capsule-v2 -->
# mypy plugin `add_method` + `__pydantic_self__` — how are synthetic methods injected without symbol clashes?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** What are the exact mechanics of inserting a generated FuncDef into a class being semantically analyzed?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/mypy.py:add_method` (:1347-1432).
**Signature:** `def add_method(api, cls: ClassDef, name: str, args: list[Argument], return_type: Type, self_type=None, tvar_def=None, is_classmethod=False) -> None`.
**Data Shape:** Mutates `cls.info.names` (SymbolTableNode with `plugin_generated=True`) and appends the FuncDef to `cls.defs.body`.

### Decisive source
```python
# remove any previously generated method with the same name to avoid redefinition churn:
if name in info.names:
    sym = info.names[name]
    if sym.plugin_generated and isinstance(sym.node, FuncDef):
        cls.defs.body.remove(sym.node)

if is_classmethod:
    self_type = self_type or TypeType(fill_typevars(info))
    first = [Argument(Var('_cls'), self_type, None, ARG_POS, True)]
else:
    self_type = self_type or fill_typevars(info)
    # As a workaround, we give this argument a name that will never conflict:
    first = [Argument(Var('__pydantic_self__'), self_type, None, ARG_POS)]
...
func = FuncDef(name, args, Block([PassStmt()]))
func.type = set_callable_name(signature, func)
...
if name in info.names:
    # keep the existing definition analyzed, under a unique alias:
    r_name = get_unique_redefinition_name(name, info.names)
    info.names[r_name] = info.names[name]
if is_classmethod:
    func.is_decorated = True
    v = Var(name, func.type); v.is_classmethod = True
    dec = Decorator(func, [NameExpr('classmethod')], v)
    sym = SymbolTableNode(MDEF, dec)
else:
    sym = SymbolTableNode(MDEF, func)
sym.plugin_generated = True
info.names[name] = sym
info.defn.defs.body.append(func)
```

**Flow:** drop prior plugin-generated twin → build signature CallableType from arguments (`__pydantic_self__` positional self for instance methods, `_cls` flagged-synthetic for classmethods) → create pass-body FuncDef → rename any pre-existing user symbol to a unique key (so it still gets ANALYZED but no longer holds the primary name) → install Decorator-wrapped node for classmethods (superclass-signature compatibility requires it even though dataclasses plugin skips it) → append to class body.
**Invariant:** The self-argument NAME is load-bearing: `self` triggers `no-redef` errors against field names; `__pydantic_self__` can't collide. Existing symbols are preserved-then-shadowed, never deleted. Every generated node must carry `plugin_generated=True` — both for cleanup on regeneration and because `add_initializer` checks that flag before refusing to overwrite user `__init__`.
**Probe:** `grep -n '__pydantic_self__' pydantic/mypy.py` (:1387) + `grep -n 'get_unique_redefinition_name(name, info.names)' pydantic/mypy.py` (:1412).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "add_method plugin_generated FuncDef classmethod", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shadow-don't-delete insertion and the unconflict-able self-name trick; adapt to your checker's node constructors; omit mypy-version pinning details.
