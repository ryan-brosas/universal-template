<!-- capsule-v2 -->
# Sticky privacy-boundary filter — how do you redact a *time interval* of activity, not just single events, while keeping the timeline shape readable?

**Source:** OpenHistory MIT `main@daf7b073ce93673d0453d9f69b7435224c4bf49c`; Codebase Memory `openhistory`. **Question:** dropping individual protected events still leaks the surrounding context; how does the source redact whole intervals and mark them without content?

## Per-browser-key enter/exit state sets emitting one-time content-free boundary sentinels
**Path/Symbol:** `src/main/privacy-policy.ts:ActivityPrivacyFilter.filter` (189-235), `:privacyBoundaryFrom` (248-258), `:filterProtectedActivityEvents` (174-181), predicate ladder `:isProtectedActivityEvent` (135-152).
**Signature:** `class ActivityPrivacyFilter { constructor(options); filter(events: ActivityEvent[]): ActivityEvent[] }` — stateful; one instance per sorted stream.
**Data Shape:** timestamp-sorted events in (caller sorts: `filterProtectedActivityEvents` re-sorts defensively); out is same-shape list where hidden spans are replaced by `{version: 1, id: "privacy-" + sha256(`${id}\n${timestamp}`).slice(0,24), timestamp, kind: "privacy_boundary"}`.

### Decisive source
```ts
if (event.kind === "privacy_boundary") { output.push(event); continue; }
if (isProtectedActivityEvent(event, this.options)) {
  const key = browserKey(event);
  if (key && isBrowserEvent(event) && isSensitiveTextField(event.element)) {
    if (!this.sensitiveBrowserFields.has(key)) output.push(privacyBoundaryFrom(event));
    this.sensitiveBrowserFields.add(key);
  }
  continue;
}
...
if (event.browser && isProtectedAdultWebDomain(event.browser.domain)) {
  if (!this.protectedBrowsers.has(key)) output.push(privacyBoundaryFrom(event));
  this.protectedBrowsers.add(key);
  continue;
}
if (event.kind === "url_changed" && this.protectedBrowsers.delete(key)) {
  output.push(privacyBoundaryFrom(event));      // exit marker itself becomes a boundary
}
if (this.protectedBrowsers.has(key)) continue;
```

**Flow:** three sticky state machines keyed by browser identity (`application bundle + browser` via `browserKey`): (1) adult-domain entry marks a browser protected until its next `url_changed`, which is CONSUMED as the exit marker and replaced by a sentinel — so the transition event cannot leak the exit URL either; (2) sensitive-field focus enters `sensitiveBrowserFields`; the first non-sensitive `focused_element_changed` exits with a final sentinel, after which focus changes flow again; while sticky, all `SENSITIVE_FOCUS_EVENT_KINDS` for that key are dropped; (3) per-event protected classes (notification bundles, messaging/mail unless opted in) are dropped silently. Boundary sentinels per transition are emitted ONCE (`has` check before `add`) so an hour-long private session adds exactly two timeline rows.
**Invariant:** zero payload of a hidden interval survives serialization (ids, labels, domains, text all gone); the timeline stays shape-preserving — every interval has exactly one enter sentinel and exactly one exit sentinel; pre-existing `privacy_boundary` control events pass through untouched.
**Probe:** `src/main/privacy-policy.test.ts:37-62` (adult interval renders as kinds `[url_changed, privacy_boundary, privacy_boundary, url_changed]` with ids `safe-before`/`safe-after` preserved and no `/pornhub|private adult action/` match) and `64-92` (password typing/snapshot dropped until safe focus; output contains neither canary password nor field identifier). Integration: `src/main/activity-event-file.test.ts:198-233` pins the whole loader path (`doesNotMatch /pornhub|private adult|arbitrary-canary-password|current-password/`). GREEN observed: `npx tsx --test src/main/privacy-policy.test.ts` → pass (4 assertion tests). The zod-dependent loader suite is blocked in this environment by missing `node_modules`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhistory", query: "privacy boundary filter protected browsers sensitive fields", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt sticky interval redaction with consumed exit markers and deduped content-free sentinels for any activity/timeline product; adapt what counts as "protected" (domain lists, field classifiers) to your domain; omit macOS accessibility roles. Coverage checked on both files: `no_recorded_issue`.
