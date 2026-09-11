<!-- capsule-v2 -->
# HTTPConnection identity façade — should two request objects wrapping the same scope ever be equal?

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `starlette`. **Question:** When a connection class doubles as a `Mapping` over the ASGI scope, what equality semantics stop scope-equal requests from collapsing into each other?

## HTTPConnection
**Path/Symbol:** `starlette/requests.py:HTTPConnection` (:80-103).
**Signature:** `class HTTPConnection(Mapping[str, Any], Generic[StateT])`; `def __init__(self, scope: Scope, receive: Receive | None = None) -> None`.
**Data Shape:** wraps one `scope` dict; Mapping protocol (`__getitem__`/`__iter__`/`__len__`) delegates 1:1 to the scope.

### Decisive source
```python
def __init__(self, scope: Scope, receive: Receive | None = None) -> None:
    assert scope["type"] in ("http", "websocket")   # constructor gate on scope kind
    self.scope = scope

def __getitem__(self, key: str) -> Any: return self.scope[key]
def __iter__(self) -> Iterator[str]:   return iter(self.scope)
def __len__(self) -> int:              return len(self.scope)

# Don't use the `abc.Mapping.__eq__` implementation.
# Connection instances should never be considered equal
# unless `self is other`.
__eq__ = object.__eq__
__hash__ = object.__hash__
```

**Flow:** any Request/WebSocket inherits this façade; `request["path"]`, `"path" in request, len(request)` all read the live scope. The Mapping ABC's default `__eq__` would compare wrapped items — making two Requests with identical scopes (every bare-metal test scope!) equal and hash-identical. Starlette overrides both back to object identity.
**Invariant:** request equality is IDENTITY, never structural — a set of requests keeps distinct entries even when every scope value matches, and dicts keyed by request never merge. Any porter who lets the Mapping default stand silently dedups middleware state.
**Probe:** coverage caveat: NO direct test pins the identity override at this pin (source-comment invariant only). Adjacent behavior tests: `tests/test_requests.py::test_request_state` (:328) exercises the façade surface without touching __eq__.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "starlette", qualified_name: "starlette.starlette.requests.HTTPConnection" });
await mcp.codebase_memory.trace_path({ project: "starlette", function_name: "HTTPConnection", direction: "inbound", depth: 2 });
```

## Verdict
Adopt identity-equality for any per-request wrapper object — it is one line and prevents an entire class of set/dict cross-request contamination. Adapt the scope-type assert if your server admits more scope kinds. Omit the Generic[StateT] plumbing unless you type state. Record the missing direct test as a caveat when porting: add `assert not (Request(scope) == Request(scope))` to your port's suite.
