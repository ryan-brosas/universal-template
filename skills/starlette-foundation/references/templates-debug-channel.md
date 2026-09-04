<!-- capsule-v2 -->
# Jinja2Templates + _TemplateResponse debug channel — context processors and response extensions

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** How does template rendering integrate with url_for and the TestClient's debug-extension plumbing?

## Jinja2Templates
**Path/Symbol:** `starlette/templating.py:Jinja2Templates` (:54-156).
**Data Shape:** constructor XOR assertion `bool(directory) ^ bool(env)` — bring your own Environment or get a FileSystemLoader with `select_autoescape()`; `_setup_env_defaults` installs a `pass_context`-decorated global `url_for(name, **params)` that resolves through the REQUEST in context (`context["request"].url_for`) — templates never need the app object.
**Flow:** TemplateResponse(request, name, ...) sets `context.setdefault("request", request)`, then layers context_processors (each a callable returning a dict to update), then renders EAGERLY at construction (template.render is sync inside __init__ of _TemplateResponse :43).
**Probe:** `tests/test_templates.py::test_calls_context_processors` (:49), `::test_templates_autoescape` (:37), `::test_templates_require_directory_or_environment` (:138).

## _TemplateResponse.__call__ — debug message emission
**Path/Symbol:** `starlette/templating.py:_TemplateResponse.__call__` (:46-51).
### Decisive source
```python
request = self.context.get("request", {})
if "http.response.debug" in request.get("extensions", {}):
    await send({"type": "http.response.debug",
                "info": {"template": self.template, "context": self.context}})
await super().__call__(...)   # normal HTML response follows
```
**Flow:** only fires when the SCOPE advertises the extension (TestClient sets it); TestClient surfaces info as `response.template/.context` attributes — test-time introspection without touching production responses.
**Probe:** `tests/test_testclient.py::test_debug_info_in_response_extensions_with_template` (:251); middleware interplay via `::test_template_with_middleware` (:77).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "_TemplateResponse", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "TemplateResponse", limit: 5 });
```

## Verdict
Adopt the pass_context url_for global and setdefault-request ordering. Adapt eager-vs-lazy rendering to your perf profile (eager = exceptions surface before send, which tests rely on). Omit the debug channel unless you port matching TestClient support.
