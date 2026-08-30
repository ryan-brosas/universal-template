<!-- capsule-v2 -->
# add_url_rule — how do methods, automatic OPTIONS, and endpoint-collision detection work at registration time?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What are the exact rules for deriving methods and the OPTIONS contract when a rule is registered?

## Rule construction + view_functions guard
**Path/Symbol:** `src/flask/sansio/app.py:App.add_url_rule` (604–661); default endpoint derivation `sansio/scaffold.py:_endpoint_from_view_func` (709–714); verb shortcuts `_method_route` (284–293).
**Signature:** `add_url_rule(rule, endpoint=None, view_func=None, provide_automatic_options: bool|None = None, **options) -> None`.
**Data Shape:** `methods` may come from the `methods` kwarg OR `view_func.methods` attr; defaults to `("GET",)`; stored uppercased into a set on the werkzeug Rule.

### Decisive source
```python
if methods is None:
    methods = getattr(view_func, "methods", None) or ("GET",)
if isinstance(methods, str):
    raise TypeError('Allowed methods must be a list of strings...')
methods = {item.upper() for item in methods}
...
if provide_automatic_options is None:
    provide_automatic_options = getattr(view_func, "provide_automatic_options", None)
    if provide_automatic_options is None:
        provide_automatic_options = (
            "OPTIONS" not in methods
            and self.config["PROVIDE_AUTOMATIC_OPTIONS"]
        )
if provide_automatic_options:
    required_methods.add("OPTIONS")
methods |= required_methods
rule_obj = self.url_rule_class(rule, methods=methods, **options)
rule_obj.provide_automatic_options = provide_automatic_options
```
Then: rule added to url_map; if view_func given and an existing DIFFERENT function occupies the endpoint ⇒ AssertionError "View function mapping is overwriting an existing endpoint function".

**Flow:** endpoint default = function `__name__` → method resolution ladder → automatic-OPTIONS decision (attr overrides arg overrides config, only when OPTIONS not already listed) → Rule into map → endpoint uniqueness assert. `@setupmethod` wrappers block all registration after the first request.
**Invariant:** registering the SAME function object twice under one endpoint is legal (idempotent re-registration); a different one raises; `methods="POST"` (a bare string) is rejected because it would register per-character methods.
**Probe:** `grep -Fc 'Allowed methods must be a list of strings' src/flask/sansio/app.py` = 1; `grep -Fc 'View function mapping is overwriting an existing' src/flask/sansio/app.py` = 1; `grep -Fc 'PROVIDE_AUTOMATIC_OPTIONS' src/flask/sansio/app.py` ≥ 1; tests `tests/test_basic.py::test_provide_automatic_options_attr_disable` (:75), `tests/test_views.py::test_view_provide_automatic_options_attr_enable` (:117).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "add_url_rule methods automatic options endpoint view functions", limit: 8 });
```

## Verdict
Adopt the three-source method ladder + per-rule `provide_automatic_options` attribute. Adapt the config key name. Omit the static-route special case (separate capsule).
