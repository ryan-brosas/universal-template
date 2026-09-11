<!-- capsule-v2 -->
# Connection class-armor and send pipeline — how do you stop shared-state footguns at the class boundary, and what runs before every command?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY, never copy verbatim. `main@2c6d9c7d`; Codebase Memory project `ext-zendriver`. **Question:** what protects Connection's class attributes from accidental mutation, and which per-connection preparations run inside the send path before your command is written?

## CantTouchThis metaclass + owner-config prep latches + target-info delegation
**Path/Symbol:** `zendriver/core/connection.py:CantTouchThis(type)` (:170-186), `Connection(metaclass=CantTouchThis)` (:189+), `SettingClassVarNotAllowedException` (:78), `__init__` (:207-226), `target` setter (:233-241), `update_target` (:528-532), `sleep` (:458-461), `wait` (:477-506, idle semantics owned by idle-breathe-readiness), `__await__` (:520-527).
**Signature:** metaclass `__setattr__(cls, attr, value)` raises `SettingClassVarNotAllowedException` (a PermissionError) for ANY class-level write EXCEPT `__annotations__` (autodoc fix); instance writes are untouched. `Connection.__init__(websocket_url, target=None, _owner=None, **kwargs)` ends with `self.__dict__.update(**kwargs)` — constructor kwargs land as instance attrs.
**Data Shape:** class-level declared attrs (`websocket`, `_current_id_mutex`, `_download_behavior`) are SHARED declarations across instances — the metaclass exists precisely so nobody mutates the CLASS object; `mapper`/`handlers`/`enabled_domains` etc. are initialized per-instance in `__init__`. Target info is delegated through ~12 read-only properties (`target_id`, `type_`, `title`, `url`, `attached`, `can_access_opener`, `opener_id`, `opener_frame_id`, `browser_context_id`, `subtype`, …) that all return None when no target is set.

### Decisive source
```python
class CantTouchThis(type):
    def __setattr__(cls, attr, value):
        if attr == "__annotations__":
            return super().__setattr__(attr, value)   # keep autodoc working
        raise SettingClassVarNotAllowedException(
            "don't set '%s' on the %s class directly, as those are shared with other objects." ...)

# send-path preamble (inside Connection.send :541-556)
await self.aopen()
if self._owner:
    if self._owner.config:
        if self._owner.config.expert:   await self._prepare_expert()    # latch _prep_expert_done
        if self._owner.config.headless: await self._prepare_headless()  # latch _prep_headless_done
if not self.listener or not self.listener.running:
    self.listener = Listener(self)
```

**Flow:** every send re-checks lazily: socket open → expert/headless one-shot preps (latched once per connection via `setattr(self, "_prep_*_done", True)`; details in headless-expert-prep-latches) → listener resurrection. `update_target()` sends `cdp.target.get_target_info(self.target_id)` with `_is_update=True` and REPLACES `self.target` with fresh TargetInfo — this runs inside `Connection.sleep()` (0.25s default breathe) and `wait()`, which is why capture helpers "sleep first" to refresh url/title state (see page-capture-download-gate). The target SETTER is the only validated write path: non-TargetInfo raises TypeError. `async with connection:` closes on exit; `await connection` == wait-for-idle. `__aexit__` re-raises the context-manager exception via `raise exc_type(exc_val)`.
**Invariants:** (1) class-level writes on any Connection subclass raise — porters who subclass and assign class attrs get a PermissionError-family exception BY DESIGN; route config through instance attrs/constructor kwargs instead (the `**kwargs` swallow-all makes extra kwargs silent instance attrs); (2) expert/headless preps are idempotent latches checked on EVERY send but executed once per socket lifetime — a reconnect (new aopen, same Connection object) does NOT reset them; (3) `target` mutations must go through the property setter or you lose TypeError validation; (4) `sleep()`/`wait()` always `update_target()` FIRST — side-effect-bearing convenience waits, not passive timers.
**Probe:** real execution (import-by-path C per cdp-transaction-generator-protocol):
```bash
python3 - <<'EOF'
class Guarded(metaclass=C.CantTouchThis): pass
try:
    Guarded.websocket = 1; raise SystemExit("metaclass guard failed")
except C.SettingClassVarNotAllowedException as e:
    assert "shared with other objects" in str(e)
g = Guarded(); g.websocket = 1          # instance write fine
assert g.websocket == 1
EOF
```
(pins: `grep -n 'class CantTouchThis' zendriver/core/connection.py` → :170; `grep -n '_prepare_expert()' zendriver/core/connection.py` → :558; `grep -n 'get_target_info' zendriver/core/connection.py` → :531; `grep -n '__dict__.update' zendriver/core/connection.py` → :217.)
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "CantTouchThis SettingClassVarNotAllowed", limit: 4 });
// ext-zendriver.zendriver.core.connection.Connection.send Method zendriver/core/connection.py 535-585
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "send transaction id mutex websocket", limit: 6 });
```
**Verdict:** ADOPT the pattern (metaclass armor over shared class-level state, latched per-connection preps inside the send path, None-safe target delegation). AGPL — reimplement, never paste.
