<!-- capsule-v2 -->
# oneshot-and-classfreezing — two connection micro-contracts: the -2 side-channel and the CantTouchThis metaclass

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** How does zendriver send must-not-interleave setup commands, and how does it stop users from corrupting shared class state?

## _send_oneshot: id -2 bypasses the mapper accounting
**Path/Symbol:** `zendriver/core/connection.py:_send_oneshot` (:710-723); `CantTouchThis` (:170-186) + `SettingClassVarNotAllowedException` (:78-79).
**Signature:** `async def _send_oneshot(self, cdp_obj: Any) -> Any`; `class Connection(metaclass=CantTouchThis)`.
**Data Shape:** oneshot transactions reuse fixed id `-2` in the mapper; used by `_prepare_headless` (UA override stripping `"Headless"`, :671-690) and `_prepare_expert` (force-open `attachShadow` script + `page.enable`, :692-708), each latched once per connection via a dynamically-set `_prep_*_done` attribute.

### Decisive source
```python
tx = Transaction(cdp_obj)
tx.connection = self
tx.id = -2
self.mapper.update({tx.id: tx})
await self.websocket.send(tx.message)
try:
    return await tx
except ProtocolException:
    pass
```
and the metaclass:
```python
class CantTouchThis(type):
    def __setattr__(cls, attr, value):
        if attr == "__annotations__":
            return super().__setattr__(attr, value)   # fix autodoc
        raise SettingClassVarNotAllowedException(
            "don't set '%s' on the %s class directly, as those are shared with other objects." ...)
```

**Flow:** `_send_oneshot` fires inside `send()`'s owner-config hook *before* the real command, deliberately outside normal id allocation so setup traffic never interleaves user ids; errors are swallowed (setup is best-effort). The listener special-cases reply id `-2` (:822-827) to complete it. The metaclass makes class-attribute assignment on `Connection` raise while instance assignment stays legal — because websocket/class-level fields are shared across connections.
**Invariant:** oneshot failures must not fail the enclosing command (bare `except ProtocolException: pass`) — headless/expert patching is advisory. And `Connection` subclass instances must set attributes on instances only; the class itself is frozen except `__annotations__`.
**Probe:** static anchors at the pin: `grep -c 'SettingClassVarNotAllowedException(' zendriver/core/connection.py` → 2; `grep -c 'id = -2' zendriver/core/connection.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "CantTouchThis setattr classvar", limit: 3 });
```

## Verdict
Adopt the negative-id side channel for any pre-command setup over a correlated transport; adopt the frozen-metaclass only if you keep shared mutable class defaults; omit the specific UA/shadow-root patches if you don't need stealth parity (they encode Chrome-version-specific strings).
