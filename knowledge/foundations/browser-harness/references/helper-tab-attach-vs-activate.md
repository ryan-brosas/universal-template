<!-- capsule-v2 -->
# Tab attach-vs-activate split — why does controlling a tab not require taking over the user's visible Chrome?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** Attaching the agent to a tab and making Chrome show it are different operations — how are they kept separate and composed?

## attach ≠ activate; blank-then-navigate; marker moves with the attached tab
**Path/Symbol:** `src/browser_harness/helpers.py:switch_tab` (:308-326), `activate_tab` (:298-306), `new_tab` (:328-350), `ensure_real_tab` (:361-373), `_target_id` (:294-296).
**Signature:** `switch_tab(target, activate=False) -> session_id`; `activate_tab(target) -> target_id`; `new_tab(url="about:blank") -> target_id`.
**Data Shape:** `_target_id` accepts a raw targetId string OR a dict from `list_tabs()`/`current_tab()` so `switch_tab(current_tab())` works.

### Decisive source
```python
def switch_tab(target, activate=False):
    target_id = _target_id(target)
    # unmark old tab: 🐴 is a surrogate pair (2 code units) + space = 3 → slice(3)
    try: cdp("Runtime.evaluate", expression="if(document.title.startsWith('🐴 '))document.title=document.title.slice(3)")
    except Exception: pass
    if activate: activate_tab(target_id)          # ONLY then take over visible tab
    sid = cdp("Target.attachToTarget", targetId=target_id, flatten=True)["sessionId"]
    _send({"meta": "set_session", "session_id": sid, "target_id": target_id})
    _mark_tab()                                    # 🐴 marker on the NEW attached tab
    return sid

def new_tab(url="about:blank"):
    # Always create BLANK then goto: passing url to createTarget RACES with
    # attach, so wait_for_load() returns before navigation actually starts.
    if url != "about:blank":
        cur = current_tab()
        if cur blank/newtab: goto_url(url); return cur  # reuse attached blank
    tid = cdp("Target.createTarget", url="about:blank", background=True)["targetId"]
    switch_tab(tid); goto_url(url) if url != "about:blank" else None
    return tid
```

**Flow:** `switch_tab` unmarks old, optionally activates, attaches, sets daemon session, marks new; `new_tab` reuses an attached blank/NTP tab else creates blank-then-navigates; `ensure_real_tab` no-ops on a real tab else switches to the first real one.
**Invariant:** attach and visible-activation are DECOUPLED (default `activate=False` keeps the user's tab); creating a tab with a URL races attach, so always blank-then-goto; the 🐴 marker is 3 UTF-16 code units so `slice(3)` cleanly removes it.
**Probe:** `tests/unit/test_helpers.py` tab tests (adjacent to fill/waits); `tests/unit/test_daemon.py:250/:285` current_tab meta path. Coverage caveat: switch/new_tab need live Chrome (integration).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "switch_tab activate attach marker slice(3)", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the attach-vs-activate split and blank-then-navigate for any browser tool; adapt marker handling; omit nothing. Coverage caveat: live-Chrome paths are integration-tested only.
