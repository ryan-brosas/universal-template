<!-- capsule-v2 -->
# JSON-navigation dual recipe — how do you read an `application/json` URL that fires no load events?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** Which readiness strategy for a JSON navigation, and how does each avoid the viewer race?

## Poll parsed innerText (large) vs frameNavigated + in-page fetch (small/medium)
**Path/Symbol:** `skills/cdp/interaction-skills/json-navigation.md` (:1-110); production instance `gsearch follow --json` (`skills/gsearch/scripts/gsearch`, poll loop verbatim).
**Signature:** recipe A: navigate → 80ms-interval poll of an expression returning `{ready, ct, len, head?|value}`; recipe B: wait for `Page.frameNavigated` commit → evaluate `(async()=>{const r=await fetch(window.location.href); …})()` with `awaitPromise:true`.
**Data Shape:** the poll expression does readiness AND projection in ONE pass — body parsed exactly once when ready.

### Decisive source
```js
var t = document.body && document.body.innerText;
if (!t) return JSON.stringify({ ready:false, ct:document.contentType, len:0 });
try { j = JSON.parse(t); } catch (e) { return JSON.stringify({ ready:false, ct:document.contentType, len:t.length, head:t.slice(0,140) }); }
return JSON.stringify({ ready:true, value:j });
...
if (v.ct && /text\/html/i.test(v.ct) && v.len > 0) throw new Error("non-JSON response (" + v.ct + "): " + v.head)
```

**Flow (A):** navigate → poll every 80ms → empty/partial = keep waiting (Chrome's JSON viewer pre-parses into innerText on its own schedule) → parse success = use the value → HTML content-type with body = throw EARLY (error page/login wall), never wait out the clock.
**Flow (B):** subscribe for the frameNavigated COMMIT (the only Page event JSON navigations fire) → same-origin `fetch(location.href)` returns raw bytes without waiting for the viewer's render → project in-page.
**Invariant:** (1) NO lifecycle event (`loadEventFired`, `networkIdle`) ever fires for `application/json` — waiting on them is a guaranteed timeout. (2) Reading `innerText` once at a fixed settle yields `''` or a truncated blob; the POLL IS the validation. (3) The content-type check converts silent error-pages into loud failures. (4) Recipe B can still be blocked by hostile endpoints even WITH page credentials — then A wins because the viewer render uses the page's own pipeline.
**Probe:** production twin pinned in gsearch's heredoc; deterministic probe: `grep -n "ready: false\|non-JSON response" skills/gsearch/scripts/gsearch skills/cdp/interaction-skills/json-navigation.md`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "frameNavigated", limit: 3, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt both recipes and the selection rule by payload size; adapt poll interval/bail heuristics to your latency budget; omitting the content-type bail turns every 404 into a 15-second hang followed by a confusing parse error.
