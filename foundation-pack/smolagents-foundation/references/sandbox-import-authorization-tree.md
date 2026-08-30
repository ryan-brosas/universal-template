<!-- capsule-v2 -->
# Import authorization tree — how are wildcard and parent-prefix import grants evaluated?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** Given an authorized-imports list containing plain names, dotted paths, `pkg.*`, and bare `*`, exactly which `import X.Y.Z` statements pass — and what does the tree walk make legal that a naive substring check would not?

## Prefix-tree walk with leaf-star wildcard
**Path/Symbol:** `src/smolagents/local_python_executor.py:build_import_tree` (:360-369), `check_import_authorized` (:372-380); consumed by `evaluate_import` (:1309-1342).
**Signature:** `build_import_tree(authorized_imports: list[str]) -> dict[str, Any]`; `check_import_authorized(import_to_check: str, authorized_imports: list[str]) -> bool`.
**Data Shape:** Each grant `"a.b"` becomes nested dicts `{a:{b:{}}}`; a literal `"*"` becomes a key `"*"` at its position in the tree. The check walks the *requested* module's dot-parts downward, returning True the moment the current node contains a `"*"` key, False if a part is missing.

### Decisive source
```python
def check_import_authorized(import_to_check: str, authorized_imports: list[str]) -> bool:
    current_node = build_import_tree(authorized_imports)
    for part in import_to_check.split("."):
        if "*" in current_node:   # star at/above this level authorizes everything below
            return True
        if part not in current_node:
            return False
        current_node = current_node[part]
    return True                   # exact or ancestor prefix match
```

**Flow:** Requested `os.path` with grants `["other","*"]` → True (root star); `Module.os` with `["Module"]` → **False** (parent grant does NOT extend to submodules); `os.path` with `["os.*"]` → True (submodule star); `os` with `["os.path"]` → True (ancestor prefix authorizes importing the parent!). The full truth table is pinned parametrized in tests (:2318-2327).
**Invariant:** Authorization is asymmetric on purpose: granting `a` allows `import a.b` (importing a submodule implies touching the parent package), but granting `a` does NOT allow attribute access to `a.b`. A porter who "fixes" the ancestor rule to require exact matches breaks `from x import y`; one who treats `"a"` as `"a.*"` reopens the whole package.
**Probe:** `tests/test_local_python_executor.py::test_check_import_authorized` (:2318-2331) + `test_additional_imports` (:765+, incl. negative cases `numpy.a` / `numpy.a.*` must raise). Live: `python3 -c` loop over the seven-case table above asserting each boolean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "check_import_authorized build_import_tree wildcard", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the exact tree semantics including the counter-intuitive rows (`os`+`["os.path"]`=True; `Module.os`+`["Module"]`=False). Adapt the grant source (smolagents seeds it from `BASE_BUILTIN_MODULES ∪ additional_authorized_imports` at both agent :1544 and executor :1721). Omit nothing: the star-position check is what makes `["*"]` a documented foot-gun ("Use this at your own risk!", evaluate_ast docstring).
