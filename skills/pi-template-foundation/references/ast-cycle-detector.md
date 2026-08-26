<!-- capsule-v2 -->
# AST circular-import detector — what is the minimal stdlib-only shape for cycle detection over Python imports?

**Source:** pi-template MIT `foundations-sync@37e9bc1736b7`; Codebase Memory `pi-template`. **Question:** How do you build an internal-import graph and report cycles without any third-party dependency?

## ast-walk adjacency + DFS stack cycle report
**Path/Symbol:** `scripts/check-circular-deps.py:get_python_files` (13–23), `resolve_module_name` (25–32), `extract_imports` (34–50), `find_cycles` (52–88).
**Signature:** `get_python_files() -> list[str]`; `resolve_module_name(path) -> str`; `extract_imports(path) -> list[str]`; `find_cycles() -> list[list[str]]`.
**Data Shape:** modules dict `{dotted-name: abspath}`; adjacency `graph[mod] -> list[internal_mod]`; cycles as node lists.

### Decisive source
```python
for mod, path in modules.items():
    imported = extract_imports(path)
    for imp in imported:
        # Check if this import resolves to an internal module
        for internal_mod in modules:
            if imp == internal_mod or imp.startswith(internal_mod + "."):
                graph[mod].append(internal_mod)

def dfs(node):
    if node in stack:
        idx = stack.index(node)
        cycles.append(stack[idx:] + [node])
        return
    if node in visited:
        return
    visited.add(node); stack.append(node)
    for neighbor in set(graph.get(node, [])):
        dfs(neighbor)
    stack.pop()
```
Import extraction covers both forms: `ast.Import` aliases AND `ast.ImportFrom` module names; parse failures degrade to `[]` (a broken file must not crash the gate). Walk skips `{.git, .venv, node_modules, site-packages, .pi}`.

**Flow:** collect .py paths outside skip dirs → resolve each to dotted module name (`__init__.py` maps to its package dir) → extract imports per file → keep only imports equal to, or a dotted child of, an internal module → DFS with an explicit stack; a node re-found IN the current stack closes a cycle recorded as `stack[idx:] + [node]`; visited-set prevents re-exploration → print each cycle as `a -> b -> a`, exit 1; else exit 0.
**Invariant:** prefix matching on dotted names (`imp == m or imp.startswith(m + ".")`) is what makes package-internal imports resolve without a real import machinery; the stack-membership test (not merely visited) is what distinguishes a CYCLE from a diamond.

**Probe:** `python3 scripts/check-circular-deps.py` executed live at the pin → stdout `No circular dependencies detected.`, exit 0 (observed 2026-08-25). Also wired as a local pre-commit hook in `.pre-commit-config.yaml`.

## Get live surrounding code
**Retrieve:** (executed at the pin)
```ts
await mcp.codebase_memory.search_graph({ project: "pi-template", query: "circular import dependency cycle detection dfs", limit: 5 });
// -> scripts.check-circular-deps.extract_imports 34-50, find_cycles 52-88, get_python_files 13-23, resolve_module_name 25-32
```

## Verdict
Adopt the whole ~99-line pattern as-is for small repos. Adapt: replace the O(modules²) inner resolution with a prefix map if the module count grows; iterate `set(graph[node])` (already deduped here) to avoid duplicate-edge blowup. Omit nothing — stdlib purity is the point.
