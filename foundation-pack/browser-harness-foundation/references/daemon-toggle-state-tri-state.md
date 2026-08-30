<!-- capsule-v2 -->
# Remote-debugging consent tri-state — how do you decide "is remote debugging on?" when Chrome's answer can be missing, stale, or a lie?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** How should a daemon interpret per-profile `chrome://inspect` toggle state without routing recovery to "click Allow" on a popup that cannot exist?

## Local State tri-state read + port-liveness anti-stale check
**Path/Symbol:** `src/browser_harness/daemon.py:remote_debugging_user_enabled` (:115-131), `_devtools_port_live` (:98-112), `remote_debugging_toggle_profiles` (:134-144); graces `NO_TOGGLE_GRACE=3` / `TOGGLE_BOOT_GRACE=12` (:94-95).
**Signature:** `remote_debugging_user_enabled() -> True | False | None`; `_devtools_port_live(base: Path) -> bool`; reads `<profile>/Local State` key `devtools.remote_debugging.user-enabled` and first line of `<profile>/DevToolsActivePort`.
**Data Shape:** `True` only when a profile records toggle-on AND its port answers a TCP connect; `False` if any profile records toggle-off; `None` when nothing conclusive is recorded. Six callers consume it as the shared consent-plane decision input (`daemon.get_ws_url`, `daemon.main`, `Daemon.start`, `admin.ensure_daemon`, `admin.start_remote_daemon`, `run._run`).

### Decisive source
```python
try:
    port = int((base / "DevToolsActivePort").read_text(...).splitlines()[0].strip())
except (OSError, ValueError, IndexError):
    return False
try:
    socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
    return True
except OSError:
    return False
```
```python
if enabled is True and _devtools_port_live(base):
    return True
if enabled is False:
    seen = False
return seen   # None == "unknown", deliberately NOT False
```

**Flow:** For each profile dir: parse Local State (tolerating OSError/ValueError/AttributeError by skipping the profile) → toggle-on counts ONLY if the port file's first line parses to an int AND something accepts a connection on 127.0.0.1:port within 0.5s → first live-on wins; any recorded-off is sticky-fallback; exhausted loop returns None.
**Invariant:** The port FILE alone is never proof of liveness — a stale DevToolsActivePort left by a closed browser must not count as a running instance (it would route self-heal to clicking an Allow popup that cannot exist). And "unknown" (None) must stay distinguishable from "off" (False): callers give unknown a grace/wait path but treat off as a hard redirect-to-consent signal.
**Probe:** Executed against pinned source with stubbed `cdp_use` import and three fake profiles: toggle-on+live listener socket → `True`; toggle-on+stale port file → `None` (not True — anti-stale holds); recorded-off → `False`. No direct unit test covers either function (`tests/unit/test_macos.py` only monkeypatches `remote_debugging_toggle_profiles` as a consumer) — coverage caveat; anchors verified at source :98-131.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "browser-harness", function_name: "remote_debugging_user_enabled", direction: "inbound", depth: 2 });
```

## Verdict
Adopt the tri-state contract (True/False/None where "unknown ≠ no") and the file-plus-socket-probe liveness rule for any state persisted beside a dead process. Adapt the 0.5s connect timeout and the Local State JSON key paths to your browser. Omit macOS AX click-recovery that consumes this signal (see `macos-consent-click-ladder`).
