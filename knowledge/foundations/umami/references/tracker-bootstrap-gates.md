<!-- capsule-v2 -->
# Tracker bootstrap & consent gates — how does an IIFE tracker script configure itself from data-attributes and respect DNT/local opt-out?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How is the tracker configured, initialized exactly once, and disabled (host allowlist, DNT, localStorage flag)?

## tracker-bootstrap-gates
**Path/Symbol:** `src/tracker/index.ts:config attrs :318-334, trackingDisabled :376-381, init :428-436, start :640-652`.
**Signature:** all config via `data-*` attributes on the script tag: `data-website-id`, `data-host-url`, `data-auto-track`, `data-do-not-track`, `data-domains`, `data-exclude-search`, `data-exclude-hash`, `data-before-send`, `data-tag`, `data-fetch-credentials`, `data-performance`.
**Data Shape:** attribute strings parsed once at IIFE entry; `'false'`/`'true'` string compares; domains comma-split.

### Decisive source
```ts
const trackingDisabled = () =>
  disabled ||                                   // server said so in a previous response
  !website ||
  localStorage?.getItem('umami.disabled') ||    // user opt-out flag
  (domain && !domains.includes(hostname)) ||    // host allowlist
  (dnt && hasDoNotTrack());                     // navigator.dnt triple-check
...
if (!window.umami) { window.umami = { track, identify, getSession } }   // idempotent global
if (autoTrack && !trackingDisabled()) {
  if (document.readyState === 'complete') init();
  else document.addEventListener('readystatechange', init, true);
}
```

**Flow:** read attributes → guard `currentScript` → define window.umami API unconditionally → auto-track only when enabled+not-disabled → `init()` runs once (`initialized` flag): initial pageview + history hooks + click hooks + optional perf observers.
**Invariant:** the API object installs even when tracking is disabled (calls become no-ops through send()'s gate) — gating the GLOBAL instead of the sends keeps host-page code from crashing. SPA navigation uses a 300ms-debounced pushState hook that skips when URL is unchanged.
**Probe:** structural pins: `grep -c "data-" src/tracker/index.ts | head -1` ≥ 1 line with many matches: `grep -o "config('[a-z-]*')" src/tracker/index.ts | wc -l` → 12.
**Probe:** `grep -n "umami.disabled" src/tracker/index.ts` → :379.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "trackingDisabled autoTrack currentScript data-website-id", limit: 10 });
```

## Verdict
Adopt attribute-driven zero-build tracker config and global-API-with-gated-sends for any embeddable script; adapt attribute names; omit msDoNotTrack legacy checks if your audience doesn't need them.
