<!-- capsule-v2 -->
# Request/Response subclass deltas — which Flask-specific knobs hang off the werkzeug base classes?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What does Flask's Request add over werkzeug's, and what are the per-request limit overrides?

## Request limits + blueprint properties; Response defaults
**Path/Symbol:** `src/flask/wrappers.py:Request` (18–219), `.max_content_length` property (59–90), `.max_form_memory_size` (92–117), `.max_form_parts` (119–144), `.blueprints` (180–195), `.on_json_loading_failed` (212–219); `Response` (222–257).
**Signature:** per-request setters `request.max_content_length = N` (3.1+); properties fall back to config when unset AND an app context exists, else to werkzeug defaults.
**Data Shape:** `_max_content_length/_max_form_memory_size/_max_form_parts` private fields shadow config values MAX_CONTENT_LENGTH / MAX_FORM_MEMORY_SIZE (500_000) / MAX_FORM_PARTS (1_000).

### Decisive source
```python
@property
def max_content_length(self):
    if self._max_content_length is not None:
        return self._max_content_length          # per-request override wins
    if not current_app:
        return super().max_content_length        # no app ctx → werkzeug default
    return current_app.config["MAX_CONTENT_LENGTH"]

@property
def blueprints(self) -> list[str]:
    name = self.blueprint                        # endpoint minus last ".x"
    if name is None: return []
    return _split_blueprint_path(name)           # ["a.b.c", "a.b", "a"] innermost-first
```
`on_json_loading_failed`: re-raises the descriptive BadRequest in debug; otherwise raises a GENERIC BadRequest (no payload leak). Response sets `default_mimetype="text/html"`, `autocorrect_location_header=False` (redirect Location stays relative), and max_cookie_size reads MAX_COOKIE_SIZE via current_app.

**Flow:** routing writes url_rule/view_args on the request during ctx.push → blueprint chain derived lazily for hook scoping → form parsing enforces the three limits with 413s.
**Invariant:** override-then-config-then-werkzeug precedence; `blueprints` is INNERMOST-FIRST because preprocess/process iterate `(None, *reversed(...))`; generic JSON errors outside debug avoid echoing attacker input.
**Probe:** `grep -Fc 'if current_app and current_app.debug:' src/flask/wrappers.py` = 1; `grep -Fc 'return _split_blueprint_path(name)' src/flask/wrappers.py` = 1; `grep -Fc 'autocorrect_location_header = False' src/flask/wrappers.py` = 1; tests `tests/test_request.py::test_max_content_length` (:9), `tests/test_basic.py::test_session_vary_cookie` uses blueprints indirectly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "Request max_content_length form limits blueprint", limit: 6 });
```

## Verdict
Adopt the three-tier limit precedence + innermost-first blueprint path. Adapt mimetype defaults. Omit json_module plumbing notes.
