<!-- capsule-v2 -->
# Handler routing ladder — how does RoutedAgent pick one handler, and what do @event/@rpc actually add?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a...`; Codebase Memory `ext-autogen`. **Question:** How are message handlers discovered, ordered, filtered, and what invariant does the strict type check enforce?

## Decorator-stamped metadata + first-matching-router dispatch
**Path/Symbol:** `python/packages/autogen-core/src/autogen_core/_routed_agent.py` (`message_handler` :85–172, `event` :205–292, `rpc` :325–412, `RoutedAgent.__init__` :460–472, `on_message_impl` :474–486).
**Signature:** `@message_handler(strict: bool = True, match: Callable[[ReceivesT, MessageContext], bool] | None = None)` applied to `async def h(self, message: ReceivesT, ctx: MessageContext) -> ProducesT`.
**Data Shape:** The wrapper function gets stamped attributes: `target_types` (from the `message:` hint, unions split), `produces_types` (from return hint), `is_message_handler = True`, and `router` — `match` or always-True; `@event` wraps router with `not ctx.is_rpc`, `@rpc` with `ctx.is_rpc`.

### Decisive source
```python
key_type: Type[Any] = type(message)
handlers = self._handlers.get(key_type)      # DefaultDict built from _discover_handlers()
if handlers is not None:
    for h in handlers:
        if h.router(message, ctx):           # first True wins, rest skipped
            return await h(self, message, ctx)
return await self.on_unhandled_message(message, ctx)
```
```python
# strict wrapper arm (message_handler/rpc):
if AnyType not in return_types and type(return_value) not in return_types:
    if strict:
        raise ValueError(f"Return type {type(return_value)} not in return types {return_types}")
```

**Flow:** class init walks `dir(cls)` collecting anything with `is_message_handler` → bucket handlers by concrete target type → on delivery, exact `type(message)` lookup (NO isinstance/MRO walk) → routers evaluated in discovery order (alphabetical attribute order) → first match runs.
**Invariant:** routing keys on the EXACT concrete type — a subclass of the declared message type will NOT route to its parent's handler (comment at :51: "this works on concrete types and not inheritance"); `strict=False` downgrades type mismatches to warnings but still executes the handler, which is a foot-gun for silent contract drift.
**Probe:** `python/packages/autogen-core/tests/test_routed_agent.py` (routing/match semantics); `tests/test_runtime.py::test_event_handler_exception_propogates` shows unhandled-message paths surfacing through the runtime.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-autogen", query: "RoutedAgent on_message_impl message_handler target_types router", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt decorator-stamped handler metadata + exact-type bucketed dispatch as the smallest complete typed router. Adapt to registry-based discovery if your host forbids `dir()` walks. Omit the Union-splitting `get_types` machinery if your messages are single-typed.
