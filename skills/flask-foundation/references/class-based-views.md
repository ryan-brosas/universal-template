<!-- capsule-v2 -->
# Class-based views — what does as_view generate, and how does MethodView infer its method table?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What per-instance/per-class choices does View.as_view make, and how are methods auto-derived?

## View.as_view + MethodView.__init_subclass__
**Path/Symbol:** `src/flask/views.py:View.as_view` (85–135), `.dispatch_request` (78–83); `MethodView` (138–191).
**Signature:** `as_view(cls, name, *class_args, **class_kwargs) -> RouteCallable`; `MethodView.dispatch_request(**kwargs)`; `http_method_funcs` frozenset (11–13) incl. the 3.2 `query`.
**Data Shape:** generated closure carries `.view_class`, `.__name__ = name`, `.__doc__`, `.__module__`, `.methods`, `.provide_automatic_options` (consumed by add_url_rule).

### Decisive source
```python
if cls.init_every_request:
    def view(**kwargs):
        self = view.view_class(*class_args, **class_kwargs)   # NEW instance/request
        return current_app.ensure_sync(self.dispatch_request)(**kwargs)
else:
    self = cls(*class_args, **class_kwargs)                    # ONE shared instance
    def view(**kwargs):
        return current_app.ensure_sync(self.dispatch_request)(**kwargs)
if cls.decorators:
    view.__name__ = name; view.__module__ = cls.__module__
    for decorator in cls.decorators:
        view = decorator(view)                                 # list order = bottom-up
...
view.view_class = cls

# MethodView auto-methods:
if "methods" not in cls.__dict__:
    for base in cls.__bases__:  methods |= base.methods or ()
    for key in http_method_funcs:
        if hasattr(cls, key): methods.add(key.upper())
```

**Flow:** registration-time instantiation decision → dispatch resolves lowercase method attr on the instance; HEAD falls back to get; unimplemented ⇒ AssertionError. Decorators wrap the FUNCTION (not the class); applying them to the class itself never affects the generated view.
**Invariant:** `init_every_request=False` shares state across requests (documented hazard — use g instead); decorators run in list order which composes bottom-up like stacking `@`s; inherited methods merge with the subclass's own http-named attrs only when the subclass doesn't declare `methods` itself.
**Probe:** `grep -Fc 'getattr(self, "get", None)' src/flask/views.py` = 1; `grep -Fc 'not in cls.__dict__' src/flask/views.py` = 1; `grep -Fc 'view.view_class = cls' src/flask/views.py` = 1; tests `tests/test_views.py::test_basic_view` (:17), `::test_view_inheritance` (:62), `::test_implicit_head` (:152).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "as_view MethodView init_every_request decorators", limit: 6 });
```

## Verdict
Adopt closure-factory + init policy + __init_subclass__ inference. Adapt ensure_sync. Omit typing-only overloads.
