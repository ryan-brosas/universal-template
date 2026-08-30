<!-- capsule-v2 -->
# Analytics Batcher people-event squashing — how do identify/increment events dedupe before hitting the wire?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What batching semantics keep people properties consistent when many set/increment calls fire between sends?

## identity-partitioned batches; increments SUM, sets LAST-WINS
**Path/Symbol:** `tracker/tracker/src/main/modules/analytics/batcher.ts` — intervals (:19–22: autosend 5 s, retry 3 s ×3), `getBatches` (:38–47), `dedupePeopleEvents` (:62–83), `squashPeopleEvents` (:85–123), endpoint `/v1/sdk/i` (:22).
**Signature:** `addEvent(event)`; `dedupePeopleEvents(): PeopleEvent[]`.
**Data Shape:** batch split by category `people|events`; people events typed e.g. `identity`, `set`, `increment_property`; squash merges payload maps — numeric values of `increment_property` ADD across occurrences (prev default 0), everything else last-wins spread.

### Decisive source
```ts
if (event.type === 'increment_property') {
  const uniqueKeys = new Set([...prevKeys, ...currKeys])
  mergedPayload[key] = (typeof prev === 'number' ? prev : 0)
                     + (typeof curr === 'number' ? curr : 0)
  ...
}
// merge payloads, taking priority to the latest one
{ ...prev.payload, ...event.payload }
```

**Flow:** events accumulate per category → every 5 s getBatches() partitions the people list at each `identity` event (identity starts a NEW part) → each part squashes same-type events → wire send with retry×3.
**Invariant:** An `identity` boundary FORBIDS merging across it (different users in one batch would corrupt attribution). Non-increment collisions take the LATEST value; increment collisions must sum.
**Probe:** `grep -c 'dedupePeopleEvents()' tracker/tracker/src/main/modules/analytics/batcher.ts` → `2`; `grep -c 'increment_property' tracker/tracker/src/main/modules/analytics/batcher.ts` → `1`; direct tests `src/main/modules/analytics/tests/people.test.ts` + `batcher.test.ts` executed green (339/339).
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "Batcher squashPeopleEvents dedupePeopleEvents increment_property", limit: 10 });
```

## Verdict
Adopt identity-partition + sum-vs-last-wins rules. Adapt categories. Omit retry ladder if you have QoS upstream.
