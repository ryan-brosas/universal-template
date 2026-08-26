<!-- capsule-v2 -->
# Headless/expert per-connection prep latches — strip the Headless tell and force-open shadow roots EXACTLY once per connection

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** how do per-tab stealth patches stay idempotent across hundreds of sends, and how do they reach the browser without disturbing the command-id stream?

## One-shot preparation inside the send path
**Path/Symbol:** `zendriver/core/connection.py:_prepare_headless` (:671-690), `_prepare_expert` (:692-708), `_send_oneshot` (:710-723), invoked from `send` (:554-560).
**Signature:** `_prepare_*(self)` gated by `getattr(self, "_prep_*_done", None)` latch attributes; `_send_oneshot(cdp_obj)` uses RESERVED transaction id `-2`.
**Data Shape:** headless prep = read `navigator.userAgent` (Runtime.evaluate, await_promise, allow_unsafe_eval_blocked_by_csp) then `Network.setUserAgentOverride` with `ua.replace("Headless", "")`. Expert prep = `Page.addScriptToEvaluateOnNewDocument` monkey-patching `Element.prototype.attachShadow` to force `{mode:"open"}` on every future document, plus `Page.enable`.

### Decisive source
```python
if getattr(self, "_prep_headless_done", None):
    return                                        # latch: once per CONNECTION, not per tab
ua = response[0].value
await self._send_oneshot(cdp.network.set_user_agent_override(user_agent=ua.replace("Headless", "")))
...
tx.id = -2                                        # reserved slot outside the counting stream
self.mapper.update({tx.id: tx})
```

**Flow:** every `send()` checks owner config: `expert` → `_prepare_expert()`, `headless` → `_prepare_headless()`; each runs once (attribute latch) then becomes a no-op for the connection's lifetime. Oneshot commands bypass normal allocation (fixed id −2, matched specially in the listener loop :822-827) and swallow `ProtocolException` — prep failures must never fail the user's actual command.
**Invariant:** the UA rewrite is a string REPLACE, not a fixed spoof — the browser's real UA minus "Headless" stays internally consistent (Chrome version matches GPU/platform), unlike shipping a canned UA that mismatches everything else. Prep order matters: patches land before ANY page-facing command because `send` runs them before allocating the user's transaction.
**Probe:** deterministic pins (no dedicated upstream test — coverage caveat; anchored at the `zendriver/` package dir): `grep -n 'ua.replace("Headless"' core/connection.py` → :687; `grep -n 'attachShadow' core/connection.py` → :699-700; `grep -n 'id = -2' core/connection.py` → :716. Family context: contrast with linkedin-profile-scraper-api's puppeteer-flag-stack NEGATIVE finding (shipping `--enable-automation`) — zendriver strips the tell at runtime instead of launching with automation flags.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "_prepare_headless set_user_agent_override attachShadow", limit: 5 });
```

## Verdict
Adopt: runtime UA-consistent stealth patch + forced-open shadow roots as one-shot per-connection latches executed inside the command path; reserved negative id channel for bootstrap commands. Adapt the specific patch set to current Chrome tells (re-verify quarterly — this is the fastest-decaying seam in the suite). Omit nothing else — the latch mechanics are the portable part. Coverage: source-pinned only.
