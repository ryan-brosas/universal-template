<!-- capsule-v2 -->
# Message-parts projection — conversation entries become [USER]/[ASSISTANT] prefixed lines, and the review window and flush window are INDEPENDENT config knobs

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** Two background consumers (review, flush) read the same session transcript with different length budgets — how do you share one projection without coupling their windows?

## collectMessageParts / applyRecentMessageLimit
**Path/Symbol:** `src/handlers/message-parts.ts` (whole file, 27 L): `collectMessageParts(entries: unknown[], recentMessages = 0)` filters `entry.type === "message"`, extracts text via `getMessageText(msg)`, prefixes `[USER]`/`[ASSISTANT]` from `msg.role`; `applyRecentMessageLimit(parts, recentMessages)` slices `-N` ONLY when `Number.isFinite(N) && N > 0`.
**Signature:** `collectMessageParts(entries, recentMessages?) → string[]`; consumed at `src/handlers/background-review.ts` (:176 collect ALL → :186 `applyRecentMessageLimit(allParts, config.reviewRecentMessages)`) and `src/handlers/session-flush.ts` (:82 `collectMessageParts(entries, config.flushRecentMessages)`).
**Data Shape:** part line = `` `${prefix}: ${text}` `` — the exact grammar the memory-lookup normalizer strips when a model pastes a rendered line back.

### Decisive source
```ts
export function applyRecentMessageLimit(parts: string[], recentMessages = 0): string[] {
  if (Number.isFinite(recentMessages) && recentMessages > 0) {
    return parts.slice(-recentMessages);
  }
  return parts;   // 0 / NaN / negative ⇒ FULL transcript, not empty
}
```

**Flow:** raw branch entries → type+text filter → role-prefixed lines → per-consumer window. The projection is PURE (no store access), so both callers can hold "all parts" and re-slice cheaply; the review path keeps the full array precisely because it slices later (:176 vs :186 are separate lines for that reason).
**Invariant:** the sentinel for "unlimited" is 0 (and any non-positive/NaN junk), NOT null or undefined-only — a porter who treats 0 as falsy-but-valid or defaults to `Infinity` breaks configs that legitimately disable the feature by omission. The two knobs (`reviewRecentMessages`, `flushRecentMessages`) must remain independent: upstream tests pin that each consumer IGNORES the other's limit.
**Probe:** `tests/handlers/session-flush.test.ts` — "Flush limits conversation to recent messages when configured" (:332) + "Flush does not use the review recent-message limit" (:348); `tests/handlers/background-review.test.ts` — "limits background review to recent messages when configured" (:391) + "does not use the flush recent-message limit for background review" (:412). Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "collectMessageParts applyRecentMessageLimit getMessageText", limit: 5 })`

## Verdict
Adopt whenever multiple consumers need differently-windowed views of one transcript. Adapt prefixes and knob names; keep the pure projection, the 0-means-unlimited sentinel, and per-consumer windows. Omit nothing — it is 27 lines whose value is the decoupling rule.
