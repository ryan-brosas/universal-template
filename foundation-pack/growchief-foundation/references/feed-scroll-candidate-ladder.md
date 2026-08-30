<!-- capsule-v2 -->
# Feed-scroll candidate ladder — how does a feed plugin guarantee it evaluates only posts actually rendered on screen before acting on one?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** the AI picked post N from an API snapshot — how does the provider reconcile that choice with what the live DOM currently shows (ids can scroll out between fetch and act)?

## Visible-selector map → shift-until-selected → scroll target into view
**Path/Symbol:** `shared/server/bots/providers/linkedin/linkedin.provider.ts:likeAndComment` (:764-987); helpers `giveLike` (:990-1024) / `giveComment` (:1026-1067); refetch loop bound `:770` (`while (content.length === 0 && totalRuns < 5)`).
**Signature:** harvest `{id, text, profile, distance}` rows from intercepted `voyagerFeedDashMainFeed` JSON; DOM reconciliation via `page.locator('//div[contains(@data-id, "urn:li:activity:")]').all()` → `mapUntilSelected = [{id, selected, text}]`.
**Data Shape:** connection filter maps `supplementaryActorInfo.text` keywords to a distance code — 'Following'→4, '3'→3, '2'→2, '1'→1, else undefined; select options: all / my-connections(1) / not-connected(2|3) / people-i-follow(4).

### Decisive source
```ts
const mapUntilSelected = getAllVisibleSelectors.map((p) => ({
  id: p, selected: p === selected?.id, text: content.find((c) => c.id === p)?.text,
}));
if (mapUntilSelected.filter((f) => f.selected).length === 0) {
  return { delay: 0, repeatJob: false, endWorkflow: false };   // chosen post NOT rendered
}
while (!mapUntilSelected[0].selected) {
  const elm = mapUntilSelected.shift();
  await cursor.scrollToElement(`div[data-id="${elm?.id!}"]`);
}
```

**Flow:** loop up to 5 times: intercept feed JSON → build BOTH a pusher list (all candidates) and a filtered content list → if empty, scroll to page bottom and retry → dedupe against ledger (`checkUsed`) → AI allowlist → `shuffle(...)[0]` picks ONE id → enumerate VISIBLE activity divs in DOM order → bail politely if the chosen id isn't among them → otherwise pop ids off the FRONT, smooth-scrolling each into view until the selected card leads → then `scrollUntilElementIsVisible` on its like glyph and dispatch giveLike/giveComment per surviving action type.

**Invariant:** acting requires VISUAL reachability, not just data presence — the while-shift loop is a scroll-driven walk of the actual render order, and `scrollToElement` itself races `scrollend` against a 3s fallback timer with a 2s settle (`bot.cursor.ts:207-238`). Randomness is seeded at selection time only (`shuffle(checkForValidOnce)[0]`) so the scroll walk stays deterministic. The 5-refetch cap bounds infinite "feed has no eligible posts" loops; exhaustion falls through with an empty content array and the run ends without action.

**Probe:** deterministic pins from repo root: `grep -cF 'voyagerFeedDashMainFeed' shared/server/bots/providers/linkedin/linkedin.provider.ts` → 1; `grep -cF 'totalRuns < 5' shared/server/bots/providers/linkedin/linkedin.provider.ts` → 1; `grep -cF 'mapUntilSelected[0].selected' shared/server/bots/providers/linkedin/linkedin.provider.ts` → 1; `grep -nF 'window.scrollTo(0, document.body.scrollHeight);' shared/server/bots/providers/linkedin/linkedin.provider.ts` → :861; `grep -cF 'img[alt=' shared/server/bots/providers/linkedin/linkedin.provider.ts` → 2 (visible-check + reaction pick inside giveLike).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "giveLike giveComment shuffle reactions", limit: 10 });
```

## Verdict
Adopt the visible-DOM reconciliation ladder (map→bail-or-walk→act) for ANY feed automation that selects from an API snapshot; adapt distance keyword codes + selectors; omit LinkedIn-specific reaction names. Coverage caveat: deterministic probes only.
