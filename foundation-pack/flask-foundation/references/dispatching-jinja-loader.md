<!-- capsule-v2 -->
# Dispatching Jinja loader — in what order are app and blueprint template folders searched?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What is the template precedence, and what does the EXPLAIN mode add?

## DispatchingJinjaLoader
**Path/Symbol:** `src/flask/templating.py:DispatchingJinjaLoader` (49–120); `render_template`/`_stream` (123–212); default ctx processor (21–33).
**Signature:** `_iter_loaders() -> Iterator[tuple[Scaffold, BaseLoader]]`; `_get_source_fast` vs `_get_source_explained`.
**Data Shape:** iteration = app loader first, then each registered blueprint's loader in registration order; first TemplateNotFound is swallowed.

### Decisive source
```python
def _get_source_fast(self, environment, template):
    for _srcobj, loader in self._iter_loaders(template):
        try:
            return loader.get_source(environment, template)
        except TemplateNotFound:
            continue
    raise TemplateNotFound(template)
```
EXPLAIN path (`config["EXPLAIN_TEMPLATE_LOADING"]`) tries ALL loaders, logs every attempt via `explain_template_loading_attempts` (debughelpers.py:124–179 — including the "looked up from an endpoint that belongs to the blueprint" hint when nothing/multiple found), then uses the FIRST success.

**Flow:** render_template → get_or_select_template → loader chain (app ⇒ blueprints) → update_template_context injects processors over `(None, *reversed(request.blueprints))`, then re-applies the CALLER's original context so explicit values always win → signals before/after render. Stream variant wraps generate() in stream_with_context.
**Invariant:** blueprint templates LOSE to app templates with the same name (app-first); caller-passed context keys beat context processors ("original wins"); the default processor substitutes concrete g/request for proxies but deliberately leaves the session proxy (accessing it would set accessed).
**Probe:** `grep -Fc 'if loader is not None:' src/flask/templating.py` = 4 (get_source×2 paths + list_templates×2); `grep -Fc 'yield self.app, loader' src/flask/templating.py` = 1; tests `tests/test_templating.py::test_original_win` (:24), `::test_template_loader_debugging` (:488), `tests/test_blueprints.py::test_templates_and_static` (:175).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "DispatchingJinjaLoader template loader blueprint", limit: 6 });
```

## Verdict
Adopt app-first dispatch + original-context-wins. Adapt EXPLAIN output format. Omit render_template_string twins (same _render core).
