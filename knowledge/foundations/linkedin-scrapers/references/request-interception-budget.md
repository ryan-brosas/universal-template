<!-- capsule-v2 -->
# Request-interception budget — how do I cut a scrape page's network cost WITHOUT breaking the app?

**Source:** linkedin-profile-scraper-api MIT `master@9fc7125`; Codebase Memory `linkedin-profile-scraper-api`. **Question:** Which requests can a scraper abort safely — and which one type breaks the whole page if blocked?

## Two-tier abort handler
**Path/Symbol:** `src/index.ts:LinkedInProfileScraper.createPage` (:296–343); host-map builder `getBlockedHosts` (:382–410) over `src/blocked-hosts.ts` (vendored MVPS hosts file — CC BY-NC-SA DATA, pattern-only).
**Signature:** `page.setRequestInterception(true)` + handler `(req) => req.abort() | req.continue()`.
**Data Shape:** tier 1 — TYPE list `blockedResources = ['image','media','font','texttrack','object','beacon','csp_report','imageset']`; tier 2 — HOST map (parsed from `0.0.0.0 <host>` lines + 10 hand-added trackers like `static.chartbeat.com`, `www.googletagmanager.com`) gating CONTENT-TYPE list `['script','xhr','fetch','document']`.

### Decisive source
```ts
// Important: Do not block "stylesheet", makes the crawler not work for LinkedIn
const blockedResources = ['image', 'media', 'font', 'texttrack', 'object', 'beacon', 'csp_report', 'imageset'];
...
if (blockedResources.includes(req.resourceType())) return req.abort()
const hostname = getHostname(req.url())
if (blockedResourcesByHost.includes(req.resourceType()) && hostname && blockedHosts[hostname] === true) {
  statusLog('blocked script', `${req.resourceType()}: ${hostname}: ${req.url()}`);
  return req.abort();
}
return req.continue()
```

**Flow:** every request passes the handler → cosmetic types die unconditionally → script/xhr/fetch/document die ONLY when the request's hostname is in the tracker set (each hit logged) → everything else continues. Host-map parse keeps only lines whose first fragment is literally `0.0.0.0` (tolerates inline comments), then merges the 10 hard-coded extras via object spread.
**Invariant:** STYLESHEETS MUST NEVER ENTER EITHER LIST — the code comment records that blocking CSS stops LinkedIn from working at all (layout-dependent hydration dies). Tier separation is the point: unconditional aborts only for resources the DOM never needed; anything carrying executable/fetch semantics requires per-host evidence. The vendored hosts FILE is CC BY-NC-SA licensed data — reuse the parse-and-set pattern, regenerate your own list from a license-compatible source.
**Probe:** no automated test covers interception — source-grounded only. Companion speed seams live in `cdp-active-lifecycle-fastpage.md` (same method, same factory): initial about:blank tab recycle (:302–305) and the raw-CDP `Page.setWebLifecycleState 'active'` + setBypassCSP block (:309–314) — wire both capsules together when porting createPage; interception alone leaves background-tab throttling on the table.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-profile-scraper-api", query: "setRequestInterception blockedResources getBlockedHosts", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier budget (type-unconditional + host-gated content) and treat the stylesheet exemption as a recorded operational gotcha, not a suggestion. Adapt the host list to your own adblock source (mind ITS license). Omit the vendored MVPS blob verbatim. Note this is a SPEED budget, not evasion — contrast `response-interception.md` (capturing payloads) and `browser-fingerprint-stealth.md` (hiding automation).
