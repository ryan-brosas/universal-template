<!-- capsule-v2 -->
# State scope write-through — what is actually shared between lifespan, requests, and app.state?

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `starlette`. **Question:** If a request mutates `request.state.x`, who else sees it — and does `app.state` participate at all?

## State + HTTPConnection.state + Router.lifespan merge
**Path/Symbol:** `starlette/datastructures.py:State` (:664-704); `starlette/requests.py:HTTPConnection.state` (:188-196); `starlette/routing.py:Router.lifespan` (:639-664); `starlette/applications.py:Starlette.__init__` (:56).
**Signature:** `State(state: dict | None = None)`; `state(self) -> StateT` property; lifespan yields `dict | None`.
**Data Shape:** State is a thin dual-protocol façade over ONE plain dict held by reference. Attribute and item protocols hit the same `_state`; KeyError on read is re-raised as AttributeError (with class name) to preserve attribute ergonomics; `__init__` must bypass its own `__setattr__` via `super().__setattr__("_state", state)` or the store would recurse into itself.

### Decisive source
```python
@property
def state(self) -> StateT:
    if not hasattr(self, "_state"):
        # Ensure 'state' has an empty dict if it's not already populated.
        self.scope.setdefault("state", {})
        self._state = State(self.scope["state"])
    return self._state
```
```python
async with self.lifespan_context(app) as maybe_state:
    if maybe_state is not None:
        if "state" not in scope:
            raise RuntimeError('The server does not support "state" in the lifespan scope.')
        scope["state"].update(maybe_state)
    await send({"type": "lifespan.startup.complete"})
```

**Flow:** lifespan contextmanager yields a dict → Router merges it into the LIFESPAN scope's `"state"` → startup.complete only sent AFTER the merge. Servers that propagate scope["state"] into per-request scopes make that dict visible as `request.state`. Requests seed an empty dict via setdefault when absent. Sharing is SHALLOW: rebinding `request.state.count += 1` writes into the shared dict only for that one request scope (TestClient copies: `"state": self.app_state.copy()`), but mutating a shared mutable VALUE (`request.state.items.append(1)`) leaks across all requests AND back into the lifespan's yielded object.
**Invariant:** `app.state` is NOT part of this chain — `Starlette.__init__` sets `self.state = State()`, a private dict never wired into any scope (:56). Porting "app.state == request.state" silently breaks lifespan seeding; conversely, assuming app-level caching via request.state breaks because each request gets a fresh copy of the server-provided state.
**Probe:** `tests/test_routing.py::test_lifespan_state_async_cm` (:645-689 — asserts count does NOT leak, items.append DOES leak, both directions); `::test_lifespan_state_unsupported` (:626-642 — RuntimeError without server state support); `tests/test_requests.py::test_request_state_object` (:292-325 — attribute+item duality, KeyError vs AttributeError).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "starlette", query: "lifespan state update scope", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "starlette", namePattern: "State", limit: 8 });
```

## Verdict
Adopt: one-dict-by-reference façade, setdefault seeding, merge-before-startup-complete, RuntimeError on unsupported servers, shallow-share semantics documented loudly. Adapt the TypedDict generics (`StatefulLifespan[AppType]`) to your typing system. Omit wiring app.state into scopes — upstream deliberately keeps them separate. All three cited files coverage-clean; 7-test subset executed green at pin.
