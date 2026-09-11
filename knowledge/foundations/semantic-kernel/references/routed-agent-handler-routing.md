<!-- capsule-v2 -->
# Routed agent handler routing — @event/@rpc/@message_handler differ only in the router's is_rpc gate

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How do the three handler decorators route by message type plus is_rpc, what happens on a type miss or a router miss, and in what order do same-type handlers run?

## message_handler/event/rpc decorators + RoutedAgent dispatch
**Path/Symbol:** `python/semantic_kernel/agents/runtime/core/routed_agent.py:message_handler` (impl 84–171), `event` (impl 219–310), `rpc` (impl 346–430), `RoutedAgent.__init__` (456–473), `on_message_impl` (475–489), `on_unhandled_message` (491–501), `_discover_handlers` (503–512).
**Signature:** `def message_handler(func=None, *, strict: bool = True, match: Callable[[ReceivesT, MessageContext], bool] | None = None)`; `async def on_message_impl(self, message: Any, ctx: MessageContext) -> Any | None`.
**Data Shape:** Each decorator builds a `MessageHandler` wrapper stashing `target_types` (from the `message` type hint, union-aware via `get_types`), `produces_types` (return hint; `AnyType` wildcard), `is_message_handler = True`, and a `router` closure. `RoutedAgent._handlers` is a `DefaultDict[type, list[MessageHandler]]`.

### Decisive source
```python
# the ONLY difference between event and rpc is the is_rpc gate:
# event (line 301):
wrapper_handler.router = lambda _message, _ctx: (not _ctx.is_rpc) and (match(_message, _ctx) if match else True)
# rpc (line 429):
wrapper_handler.router = lambda _message, _ctx: (_ctx.is_rpc) and (match(_message, _ctx) if match else True)
# message_handler (line 169): no is_rpc gate at all
wrapper_handler.router = match or (lambda _message, _ctx: True)

# dispatch: first router-True handler wins, same-type handlers in alphabetical attribute order
async def on_message_impl(self, message, ctx):
    handlers = self._handlers.get(type(message))
    if handlers is not None:
        for h in handlers:
            if h.router(message, ctx):
                return await h(self, message, ctx)
    return await self.on_unhandled_message(message, ctx)
```

**Flow:** Decoration time: `get_type_hints` extracts the message hint (missing → AssertionError at import) and return hint; the wrapper type-checks message and return at call time — `strict=True` (default) raises `CantHandleException` (message) or `ValueError` (return); `strict=False` degrades both to warnings. `@event` additionally rejects a non-None return (ValueError when strict). `RoutedAgent.__init__` discovers handlers via `dir(cls)` + the `is_message_handler` attribute (class-level getattr, so self is unbound) and buckets them by target type. Dispatch: exact `type(message)` lookup, first handler whose router returns True wins; a router miss (or no handler for the type) falls back to `on_unhandled_message`, which logs and does NOT raise. The `match` callable is secondary routing among handlers for the SAME type — docstring: tried in alphabetical attribute order, first match called, rest skipped.
**Invariant:** An event handler can never receive an RPC message and vice versa — the router's is_rpc gate is the sole discriminator, and `MessageContext.is_rpc` is set by the envelope kind (`_process_send` → True, `_process_publish` → False). A message with no matching handler is never an error at the agent level.
**Probe:** `python/tests/unit/agents/runtime/test_runtime.py::test_register_receives_publish_cascade` (line 230 — CascadingAgent's `@message_handler` republishes until max_rounds; per-agent call count = 5·(4^i) summed), `test_default_subscription` (289) and `test_type_subscription` (314) — publish reaches the default-key instance only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "RoutedAgent message_handler event rpc router is_rpc target_types on_message_impl on_unhandled_message", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the decorator-stashes-metadata + router-closure shape (type routing at decoration, is_rpc as the event/rpc discriminator, first-router-True dispatch with alphabetical tie order, log-don't-raise unhandled fallback). Adapt strict-mode behavior to your host's error policy. Omit the `AnyType` return wildcard if your host has no dynamic return typing.
