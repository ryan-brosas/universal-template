<!-- capsule-v2 -->
# TagWatcher two-tier matching + IntersectionObserver trigger — how do server-defined element tags fire exactly once on render?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What lookup structure and observation policy make "start recording when this selector appears" cheap and single-shot?

## Fingerprint maps (id/data-attr/class) → fallback matches(); unobserve after fire
**Path/Symbol:** `tracker/tracker/src/main/modules/tagWatcher.ts` — storage key `__or__watched_tags__` (:3), 500 ms poll `setTags` (:61–80), observer callback (:27–40), `onTagRendered` (:82–89); matcher `tagMatcher.ts` (`lastSegment` combinator split, byId/byDataAttr/byClass maps, parent+children probe in `match`, `matchesLocation` path/href equality).
**Signature:** `match(el: Element): Tag | null`; `matchesLocation(tag): boolean`.
**Data Shape:** Tag `{id:number, selector:string, location?:string}`; location starting `/` compares pathname, else full href; poll interval 500 ms; sessionStorage cache survives reloads.

### Decisive source
```ts
this.observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      const tag = entry.target.__or_watcher_tagname
      if (tag) { this.onTagRendered(tag) }
      this.observer.unobserve(entry.target)   // one-shot
```
```ts
// tagMatcher: last combinator-separated segment drives the fast map...
const parts = trimmed.split(/\s*[>+~ ]\s*/)
```

**Flow:** tags fetched from `/v1/web/tags` (auth'd), cached in sessionStorage → poller queries each selector, stamps first hit with its tag id → IntersectionObserver watches candidates → visibility ⇒ emit TagTrigger message and stop observing that element. Matcher resolves an element (or parent/child) via id/data-attr/class fingerprints, falling back to native matches().
**Invariant:** A fired tag is REMOVED from the candidate list before re-arming; location mismatch after render cancels the trigger without re-arming. Fingerprint miss must fall through to full selector matching or nested selectors break.
**Probe:** `grep -c '__or__watched_tags__' tracker/tracker/src/main/modules/tagWatcher.ts` → `1`; `grep -c 'unobserve(entry.target)' tracker/tracker/src/main/modules/tagMatcher.ts tracker/tracker/src/main/modules/tagWatcher.ts` → per-file sum 1+1=2 lines; direct tests `tests/tagWatcher.test.ts` + `tests/tagMatcher.test.ts` executed green.
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "TagWatcher TagMatcher matchesLocation setTags", limit: 10 });
```

## Verdict
Adopt fingerprint-first matching + one-shot observation. Adapt storage/transport. Omit location scoping if global.
