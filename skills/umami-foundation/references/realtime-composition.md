<!-- capsule-v2 -->
# Realtime aggregation composition — how do you build the live-view payload (activity + series + totals) from three parallel queries?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How is the realtime dashboard payload assembled, and what are the dedup/classification rules for events?

## realtime-composition
**Path/Symbol:** `src/queries/sql/getRealtimeData.ts:getRealtimeData :12-77`; inputs getRealtimeActivity (limit 100, desc), getPageviewStats, getSessionStats.
**Signature:** `getRealtimeData(websiteId, filters) -> { countries, urls, referrers, events[], series{views,visitors}, totals{views,visitors,events,countries}, timestamp }`.
**Data Shape:** activity rows `{sessionId,urlPath,referrerDomain,country,eventName}`; uniques Set dedupes sessions for country counts.

### Decisive source
```ts
const { countries, urls, referrers, events } = activity.reverse().reduce((obj, event) => {
  if (!uniques.has(sessionId)) {
    uniques.add(sessionId);
    increment(countries, country);
    events.push({ __type: 'session', ...event });     // first sight of a session
  }
  increment(urls, urlPath);                            // pageviews count every hit
  increment(referrers, referrerDomain);
  events.push({ __type: eventName ? 'event' : 'pageview', ...event });
  return obj;
}, {...});
...
events: events.reverse(),                              // restore newest-first for the feed
```

**Flow:** Promise.all three queries → reverse to chronological → fold with session-dedup side effects → reverse again for display. Totals come from the SERIES arrays (`reduce sum y`), not separate queries.
**Invariant:** classification is per-row at fold time (`eventName ? 'event' : 'pageview'`, plus synthetic `__type:'session'` markers) — the client renders directly from these tags. The double-reverse is load-bearing: SQL returns desc; the reducer needs asc to mark the FIRST occurrence of each session.
**Probe:** structural pins: `grep -c "reverse()" src/queries/sql/getRealtimeData.ts` → 2; `grep -n "__type" src/queries/sql/getRealtimeData.ts | head -2` → :44,:48 region.
**Probe:** `grep -n "Promise.all" src/queries/sql/getRealtimeData.ts` → :14.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "getRealtimeData uniques increment totals", limit: 10 });
```
**(Retrieve:)**

## Verdict
Adopt single-fold composition with session-dedup markers for realtime feeds; adapt limits and window (5 min in getActiveVisitors); omit series-summing if your backend returns totals natively.
