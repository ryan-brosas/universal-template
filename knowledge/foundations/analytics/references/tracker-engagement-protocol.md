<!-- capsule-v2 -->
# Tracker engagement protocol — client-side engaged-time accounting and the 3-second/scroll-depth send gate

**Source:** Plausible Analytics AGPL-3.0 `master@9cc669b9`; Codebase Memory `ext-analytics`. **Question:** When exactly does the tracker emit an `engagement` event, and how is `engagement_time` computed across tab visibility changes and SPA navigations?

## Visibility-driven accumulation FSM
**Path/Symbol:** `tracker/src/engagement.js:onVisibilityChange` (:89-103), `getEngagementTime` (:115-121), `triggerEngagement` (:48-87).
**Signature:** module-level vars: `runningEngagementStart` (timestamp while page visible+focused, else 0), `currentEngagementTime` (banked ms), `currentEngagementMaxScrollDepth` (sent high-water), `listeningOnEngagement` (SPA re-entry latch).
**Data Shape:** payload `{n:'engagement', sd: rounded %, d: domain, u: url, p: props, e: engagement_ms, v: version[, h:1 hash-mode]}`; missing scroll_depth server-defaults to 255 (`Request.@missing_scroll_depth`).

### Decisive source
```js
if (!currentEngagementIgnored &&
    (currentEngagementMaxScrollDepth < maxScrollDepthPx || engagementTime >= 3000)) {
  currentEngagementMaxScrollDepth = maxScrollDepthPx
  ...
  runningEngagementStart = 0   // banked time resets AFTER successful gate
  currentEngagementTime = 0
}
```

**Flow:** pageview → reset counters + register listeners ONCE → hidden/blur banks elapsed time + fires triggerEngagement → visible+focus resumes clock only if `runningEngagementStart === 0`. SPA pageviews call `prePageviewTrack` which triggers the PREVIOUS page's engagement before resetting height/scroll state.
**Invariant:** (1) Send gate is monotonic scroll OR ≥3000ms since last send — first event always sends (initial scroll depth); (2) `e` measures ENGAGED time only (visible AND focused), never wall-clock — server sums it as `engagement_time` for time_on_page; (3) max-scroll-depth is a high-water mark compared BEFORE send so repeated tab toggles don't resend identical depth.
**Probe:** `tracker/test/engagement.spec.js:296` ("sends engagement events when tab toggles between foreground and background") + `:325` ("does not send engagement events when tab is only open for a short time until over 3000ms has passed").
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", file_pattern: "tracker/src/engagement.js", limit: 10 });
```

## Server-side validation of the same contract
**Path/Symbol:** `lib/plausible/ingestion/request.ex:put_engagement_fields` (:346-369) + `@missing_scroll_depth 255 / @too_large_engagement_time` kludge (:31-40).
**Flow:** engagement events REQUIRE at least one of valid `sd` or `e` else changeset error ("engagement event requires a valid integer value…"); huge legacy values (>30 days) clamped while old cached scripts rotate out.
**Invariant:** Client and server encode the SAME protocol constants — porting one without the other breaks ingestion for old clients. The `interactive?` flag from the tracker decides bounce semantics in CacheStore (`update_session`).
**Probe:** `grep -n 'blank_engagement_error_message' lib/plausible/ingestion/request.ex` → :40 def + :358 use.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-analytics", file_pattern: "ingestion/request.ex", fields: ["lines"], limit: 12 });
```

## Verdict
Adopt visibility-banked engaged-time + monotonic-depth send gate; adapt thresholds; omit COMPILE_* variant flags specific to Plausible's script bundling.
