<!-- capsule-v2 -->
# DevToolsActivePort browser discovery ladder — how do you find and order every running Chromium without assuming port 9222?

**Source:** browser-harness-js MIT `main@6b189406`; Codebase Memory `browser-harness-js`. **Question:** How does auto-detect enumerate browsers, read their real debug endpoints, and pick the winner?

## Hardcoded candidates + bounded fallback scan, mtime-recency ordering, two-line file protocol
**Path/Symbol:** `skills/cdp/sdk/session.ts:detectBrowsers` (:553-578), `getBrowserCandidates` (:583-632), `scanForExtraBrowsers` (:662-699), `tryReadDevToolsActivePort` (:706-720), `readDevToolsActivePort` polling twin (:500-520).
**Signature:** `detectBrowsers(): Promise<DetectedBrowser[]>` where `DetectedBrowser = { name, profileDir, port, wsPath, wsUrl: 'ws://127.0.0.1:<port><wsPath>', mtimeMs }`.
**Data Shape:** candidates are `{name, profileDir}` per-OS lists in rough popularity order (Dia/Helium first — the author's browsers); a valid `DevToolsActivePort` is line1 = finite port number, line2 = path starting `/devtools/`.

### Decisive source
```ts
const [portStr, path] = text.trim().split('\n');
const port = Number(portStr);
if (!Number.isFinite(port)) return undefined;
if (!path || !path.startsWith('/devtools/')) return undefined;
return { port, path, mtimeMs: st.mtimeMs };
...
detected.sort((a, b) => b.mtimeMs - a.mtimeMs);   // most-recently-launched first = connect()'s default pick
```
Fallback scan walks exactly two levels under each OS browser-data root, probing four layouts:
```
<root>/<product>/DevToolsActivePort                     (Comet, Vivaldi, Edge, Aside)
<root>/<product>/User Data/DevToolsActivePort           (Arc, Dia)
<root>/<vendor>/<product>/DevToolsActivePort            (Google/Chrome)
<root>/<vendor>/<product>/User Data/DevToolsActivePort  (Windows)
```
with dotfile entries skipped and every readdir/stat failure swallowed; `seen` dedupes against the hardcoded list AND accumulates fallback hits.

**Flow:** explicit candidate list → `tryReadDevToolsActivePort` per profile → merge bounded fallback scan → sort mtime desc. `connect()` with no args then tries each `wsUrl` most-recent-first; dead ports / 403s fail in <100ms each.
**Invariant:** (1) NEVER assume 9222 — Chrome 144+ toggled from chrome://inspect doesn't serve `/json/version`, so the DevToolsActivePort file is the ONLY reliable discovery for it (`resolveWsUrlFromPort` falls back from the HTTP probe to this scan). (2) The polling variant (`readDevToolsActivePort`, 30s deadline / 250ms interval) exists because Chrome writes the file atomically and the path line can lag the port line on first open — a single read races the browser's own startup. (3) Recency ordering is the selection policy; a porter sorting by name changes which browser silently wins multi-browser machines.
**Probe:** direct test `skills/cdp/sdk/session.test.ts` pins `getBrowserCandidates` Helium paths on all three platforms (:5-29). Discovery ordering itself is source-pinned: `grep -n "mtimeMs - a.mtimeMs\|startsWith('/devtools/')" skills/cdp/sdk/session.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness-js", query: "detectBrowsers", limit: 3, fields: ["signature", "name", "file"] });
// resolves session.detectBrowsers @ session.ts:553-578
```

## Verdict
Adopt the two-line-file protocol + recency ordering + two-level fallback scan for any "attach to the user's running browser" tool; adapt the hardcoded candidate list (add your own browsers at the front); omit Windows layouts if you're single-platform. The Helium test is your template for extending the candidate list safely.
