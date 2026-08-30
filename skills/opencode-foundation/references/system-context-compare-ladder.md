<!-- capsule-v2 -->
# System-context compare ladder — how do you refresh multi-source privileged context per source without re-rendering the whole baseline, while keeping the durable state decodable and comparable?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** A model-facing system context is composed of independently refreshable typed sources (environment, date, instructions, skills). Each can change, fail to observe, or disappear mid-session. How do you compare current observations against durable state and produce either an incremental update, a full replacement, or an honest block — never a silently incomplete baseline?

## Source algebra and the opaque carrier
**Path/Symbol:** `packages/core/src/system-context/index.ts` (`Key` :22, `unavailable` :28, `Source<A>` :32, `make` :135, `combine` :176, `observe` :182, `initialize` :198, `reconcile` :218, `reconcileObservation` :228, `replace` :283, `replaceObservation` :287, `requireText` :309, `assertUniqueKeys` :318).
**Signature:** `make<A>(source: Source<A>): SystemContext`; `initialize(ctx) → Effect<Generation, InitializationBlocked>`; `reconcile(ctx, previous: Snapshot) → Effect<ReconcileResult>`; `replace(ctx, previous) → Effect<ReplacementResult>`.
**Data Shape:** `SourceSnapshot = { value: Schema.Json, removed?: NonEmptyString }`; `Snapshot = Record<Key, SourceSnapshot>`; `ReconcileResult = Unchanged | Updated{text, snapshot} | ReplacementReady{generation} | ReplacementBlocked`.

### Decisive source
```ts
// index.ts:228-281 — reconcileObservation: the compare ladder
const compared = entry.compare(stored.value)
if (compared._tag === "Incompatible") return { _tag: "Replace" }
...
for (const key of Object.keys(previous).sort()) {
  if (keys.has(Key.make(key))) continue
  if (previous[key].removed === undefined) return { _tag: "Replace" }   // vanished without removal text
}
...
if (entry._tag === "Unavailable") {
  if (stored) snapshot[entry.key] = stored   // absence ≠ removal: keep admitted snapshot
  continue
}
```

**Flow:** observe loads every source concurrently (one coherent observation per transition). initialize fails with InitializationBlocked (listing keys) if ANY source is unavailable — no partial baseline is ever admitted. reconcile decodes each stored value with the source codec: decode failure → Incompatible → escalate to Replace; equivalence (Schema.toEquivalence) → Unchanged; else Updated with the source's own update text. A source present before but absent now emits its stored `removed` text if it has one, otherwise escalates to Replace (you cannot honestly render a removal you never planned for). Unavailable sources retain their stored snapshot and render nothing. replace blocks (ReplacementBlocked) while an ADMITTED source is unavailable; with no admitted-but-unavailable source it re-renders everything from the same single observation.
**Invariant:** unavailable ≠ removed — refresh preserves the admitted snapshot; a replacement is never constructed from a partial observation; empty model-visible renderings are defects (requireText throws); duplicate keys die at combine() before any observation; updates and removals render in stable sorted key order.
**Probe:** `packages/core/test/system-context/index.test.ts` (18 `it.effect` cases): "retains admitted snapshots while a source is temporarily unavailable" pins Unchanged + ReplacementBlocked + ReplacementReady-on-empty-previous; "requests replacement when a stored value no longer decodes" pins Incompatible→Replace; "requests replacement when a source without removal text disappears" pins the vanished-no-removal escalation; "renders multiple removals in stable key order" pins `Removed a\n\nRemoved z`; "does not render discarded updates while replacing" pins zero update-render calls on the Replace path; "rejects empty model-visible renderings" pins the requireText defect. Source pin:
```bash
grep -c 'Incompatible' packages/core/src/system-context/index.ts   # expect 4
grep -n 'rendered an empty' packages/core/src/system-context/index.ts   # expect 1 (:310)
grep -c '_tag: "Replace"' packages/core/src/system-context/index.ts   # expect 3
grep -c 'ReplacementBlocked' packages/core/src/system-context/index.ts   # expect 4
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "SystemContext reconcile Incompatible ReplacementBlocked unavailable removal text codec equivalence", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-source snapshot {value, removed?} with the three-way reconcile outcome and the Incompatible→Replace escalation; adopt "unavailable keeps the admitted snapshot" and "replacement blocked while admitted sources are unobservable"; adopt removal-text-or-replace for vanished sources. Adapt the codec/equivalence machinery to your schema library; omit the InitializationBlocked all-or-nothing gate if your sources cannot fail transiently. Direct tests read whole (index.test.ts 307L); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
