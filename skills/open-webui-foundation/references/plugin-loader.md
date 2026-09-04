<!-- capsule-v2 -->
# DB-stored plugin loader — how does user-authored Python from a database row become an importable module without corrupting sys.modules?

**Source:** open-webui "Open WebUI License" `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** How is untrusted DB content exec-loaded safely for repeated use, and what exactly happens on a failed load?

## Synthetic module exec + failure containment
**Path/Symbol:** `backend/open_webui/utils/plugin.py:load_function_module_by_id` (259-315), `load_tool_module_by_id` (206-256), `replace_imports` (187-201), `get_function_module_from_cache` (375-416), `extract_frontmatter` (151-184), `install_frontmatter_requirements` (422-450).
**Signature:** `async def load_function_module_by_id(function_id: str, content: str | None = None)`; tool twin takes `tool_id`. Returns `(instance, type, frontmatter)`.
**Data Shape:** synthetic module name `function_{id}` / `tool_{id}` registered in `sys.modules`; temp file supplies `__file__`; frontmatter is a triple-quote manifest dict (`title/description/version/requirements...`); dispatch classes: `Pipe | Filter | Action | Event` (functions) vs `Tools` (tools).

### Decisive source
```python
module_name = f'function_{function_id}'
module = types.ModuleType(module_name)
sys.modules[module_name] = module
...
exec(content, module.__dict__)
...
except Exception as e:
    del sys.modules[module_name]                      # scrub the namespace
    await Functions.update_function_by_id(function_id, {'is_active': False})
    raise e                                           # functions deactivate;
finally:                                              # tools only scrub
    os.unlink(temp_file.name)
```

and the per-request cache contract:
```python
if load_from_db:
    # inlet/outlet: always re-read the row; rewrite imports and persist
    new_content = replace_imports(content)
    if new_content != content:
        await Functions.update_function_by_id(function_id, {'content': content})
    if function_contents_cache.get(function_id) == content:
        return functions_cache[function_id], None, None   # unchanged -> reuse
else:
    # stream hook: cache-only, no DB read per token
    if function_id in functions_cache:
        return functions_cache[function_id], None, None
```
**Flow:** `ENABLE_PLUGINS` gate → content source: DB row (rewritten via `replace_imports`: `from utils/main/config/apps` → `from open_webui.*`, persisted back) or provided string (frontmatter requirements installed via `asyncio.to_thread` so pip never blocks the loop) → register synthetic module, write temp file as `__file__`, exec → class-shape dispatch instantiates the first matching class → callers cache modules keyed by id with content-hash short-circuit.
**Invariant:** a failed load always removes the synthetic module from `sys.modules` and unlinks the temp file, but only *functions* additionally flip `is_active: False` so the scheduler stops selecting them — tools raise without auto-deactivation; unchanged content reuses the cached module instead of re-execing.
**Probe:** no test runner at this HEAD — deterministic anchor executed: `grep -n "'is_active': False" backend/open_webui/utils/plugin.py` hits line 312 (inside the function-loader except block only). Known quirk worth porting deliberately: `replace_imports` uses bare `str.replace`, so it can rewrite unintended substrings like `from utils_extra`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "load_function_module_by_id load_tool_module_by_id frontmatter requirements sys.modules", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the synthetic-module hygiene (register-before-exec, temp `__file__`, guaranteed unregister/unlink) plus the functions-deactivate/tools-don't split and the content-hash module cache; adapt import rewriting and requirement installation to your package manager; omit the specific frontmatter manifest schema. Coverage caveat: none recorded for these paths; direct tests absent repo-wide.
