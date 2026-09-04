<!-- capsule-v2 -->
# debugger-python-formatter-plane — how do you visualize non-JVM types in gdb/lldb from inside a JVM IDE?

**Source:** JetBrains installed distributions (proprietary), RustRover decisive instance. **Question:** Where do Rust debug visualizers live, and how do they stay compatible across debugger versions and ABIs?

## plugins/intellij-rust/prettyPrinters/: gdb + lldb python provider pairs with .pyi host-API stubs
**Path/Symbol:** `rustrover/plugins/intellij-rust/prettyPrinters/rust_types.py` (shared classifier vocabulary) + `gdb_formatters/{gdb_lookup,gdb_providers}.py` (+`gdb/__init__.pyi`) + `lldb_formatters/lldb_providers.py` (+`lldb/{__init__,formatters}.pyi`) — graph symbols `jetbrains-rustrover.plugins.intellij-rust.prettyPrinters.gdb_formatters.gdb_lookup.{register_printers,classify_rust_type,lookup,is_old_enum,is_new_enum}`.
**Signature:** `register_printers(objfile)` → `objfile.pretty_printers.append(lookup)`; `lookup(valobj) -> object` dispatches on `classify_rust_type(valobj.type) -> RustType` (~25 variants: STRUCT/TUPLE/ENUM/STRING/OS_STRING/STR/SLICE/VEC/VEC_DEQUE/BTREE_SET/BTREE_MAP/HASH_MAP/HASH_SET/RC[+WEAK]/ARC[+WEAK]/RC_INNER_STR[_MSVC]/RC_INNER_SLICE[_MSVC]/CELL/REF[_MUT]/REF_CELL/NONZERO_NUMBER/RANGE…).
**Data Shape:** one lookup function per debugger family; providers are classes constructed with the debugger value wrapper; `rust_types.py` classifies via DWARF type codes + struct tag names; `.pyi` stubs (`gdb/__init__.pyi`, `lldb/formatters.pyi`) type the HOST debugger API for tooling only — they never execute.

### Decisive source
```python
# gdb_formatters/gdb_lookup.py (retrieved via mcp get_code_snippet)
def register_printers(objfile):
    objfile.pretty_printers.append(lookup)

# Enum representation in gdb <= 9.1
def is_old_enum(valobj): ...
# Enum representation in gdb >= 10.1
# Introduced in https://github.com/bminor/binutils-gdb/commit/9c6a1327ad9a92b8584f0501dd25bf8ba9e84ac6
def is_new_enum(type):
    fields = type.fields()
    if len(fields) > 1:
        field0 = fields[0]
        if field0.artificial and field0.name is None and field0.type.code == TYPE_CODE_INT:
            return True
    return False

def classify_rust_type(type):
    if type.code == TYPE_CODE_STRUCT:
        return RustType.ENUM if is_new_enum(type) else classify_struct(type.tag, type.fields())
    if type.code == TYPE_CODE_UNION:
        return classify_union(type.fields())
    return RustType.OTHER
```

**Flow:** native debug session starts under gdb or lldb → IDE registers the matching formatter module into the debugger's python runtime → each variable's type is classified → enum ABI probed (old union-of-fields vs new artificial unnamed int discriminant) → provider renders children/summary; MSVC-suffixed RustType variants (RC_INNER_STR_MSVC…) handle non-DWARF layouts.
**Invariant:** the SAME logical type may need TWO detection paths (debugger-version ABI drift) and layout-specific providers per C++ ABI; registration must be idempotent per objfile; the plane must be pure-python and importable by the debugger's embedded interpreter (no JVM involvement at render time).
**Probe:** `python3 -c "import ast;src=open('rustrover/plugins/intellij-rust/prettyPrinters/gdb_formatters/gdb_lookup.py').read();t=ast.parse(src);print(sorted(n.name for n in t.body if isinstance(n,ast.FunctionDef)))"` → `['classify_rust_type','is_new_enum','is_old_enum','lookup','register_printers']`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-rustrover", query: "classify_rust_type register_printers lookup", file_pattern: "plugins/intellij-rust/**", limit: 8 });
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-rustrover", qualified_name: "jetbrains-rustrover.plugins.intellij-rust.prettyPrinters.gdb_formatters.gdb_lookup" });
```
(both executed live this pass; coverage freshness metadata_match.)

## Verdict
Adopt: ship per-debugger python visualizer modules registered via the debugger's own printer API, with an explicit ABI/version probe before choosing a provider and .pyi stubs documenting the host API surface. Adapt: classification vocabulary to your language's types. Omit: Rust std-type specifics. Caveat: lldb side verified by symbol listing only (providers exist; entry script not excerpted this pass).
