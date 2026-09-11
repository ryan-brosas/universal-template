<!-- capsule-v2 -->
# WS payload limit + in-page fetch replay — how do you move data through CDP without killing the socket, and why must HTTP replay run INSIDE the page?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** What are the size rules for every `returnByValue` response, and where do authenticated requests execute?

## 256KB/3-divisible slices; project-in-page or write server-side; fetch(window.location.href) carries cookies/origin
**Path/Symbol:** `skills/cdp/interaction-skills/connection.md` (payload limits :115-133); `media-capture.md` slice math (:83-125); `json-navigation.md` + `reverse-engineer-api.md` (replay-from-page rule).
**Signature:** pattern, not one symbol: big values NEVER cross the wire whole; page-side helper `__pullBuffer(i, offset, len)` returns base64 of a bounded slice.
**Data Shape:** safe slice = 262143 bytes = 256KB−1 = 3 × 87381; sub-chunks ≤ 49998 bytes (`fromCharCode.apply` arg-stack limit, divisible by 3).

### Decisive source
```md
The CDP WebSocket has a per-message size limit. A single response large enough
to exceed it closes the socket … Common culprits: getFullAXTree on a giant page,
Runtime.evaluate with returnByValue returning a huge object, Network.getResponseBody,
DOM.getDocument with deep depth.
1. Don't pipe big blobs back through /eval — write large data to a file server-side.
2. Scope or limit the response at the source (getPartialAXTree, clipped strings,
   DOM.getDocument({depth:1})).
```
```md
Each slice ≤ 256KB (262143 bytes). The slice length is divisible by 3. Base64
encodes 3 bytes → 4 chars; a 3-aligned length means each slice's base64 is
independently decodable with no interior padding. Proven: a 4MB slice from the
same buffer drops the socket on the first call; a 256KB slice survives.
```
Replay rule:
```md
fetch() run via Runtime.evaluate executes inside the page with the page's
credentials and origin. A request sent from Node … has a different fingerprint
and gets blocked. Don't replay from outside the browser.
```

**Flow:** anticipate size → either project DOWN in-page and return the small projection, write to disk server-side from the daemon, or drain via repeated small slices appended node-side → for authenticated API reads, capture the request contract from Network events then re-issue it as an in-page `fetch(..., {credentials:'include'})` so cookies/origin/referer ride along; re-capture auth tokens fresh each session.
**Invariant:** (1) The limit is a CONNECTION property: any oversized response kills the shared WS for ALL sessions — hence repo-wide discipline. (2) After a drop, `_call` auto-heals but flat sessions die (`-32001`) — re-attach and continue. (3) In-page vs Node-side fetch is an AUTH boundary, not a style choice. (4) Anti-bot endpoints can still refuse the in-page fetch → fall back to reading Chrome's own JSON-viewer render of `document.body.innerText`.
**Probe:** no unit test (live-network physics). Deterministic probe: constants pinned in docs — `grep -n "262143\|49998" skills/cdp/interaction-skills/media-capture.md`; measured claim (4MB fails / 256KB survives) recorded by the author.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "returnByValue", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the slice/project/server-write triage for any tool that shuttles bulk data over a per-message-limited channel; adapt slice size downward for stricter transports; never move authenticated replay out-of-page without accepting bot-fingerprint blocks.
