<!-- capsule-v2 -->
# SkipLimitScroller — offset pagination with a sticky end-of-results latch (how do I page by skip/limit without re-hitting a dead end)?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** How should an offset/limit paginator behave once the source returns an empty page — and what does correct back-stepping look like?

## The abstract scroller
**Path/Symbol:** `src/scrollers/skip-limit-scroller.ts:SkipLimitScroller` (:3–59).
**Signature:** `abstract class SkipLimitScroller<T> { limit: number; skip: number; scrollNextCounter = 0; hitEndOfResults = false; abstract fetch(): Promise<T[]>; scrollNext(); scrollBack(); restart() }`.
**Data Shape:** `skip` advances by `limit` per call; `hitEndOfResults` is the latch; `scrollNextCounter` counts successful forward pages.

### Decisive source
```ts
async scrollNext(): Promise<T[]> {
  if (this.hitEndOfResults) { return []; }
  const results = await this.fetch();
  if (isEmpty(results)) { this.hitEndOfResults = true; }
  this.skip += this.limit;
  this.scrollNextCounter += 1;
  return results;
}
async scrollBack(): Promise<T[]> {
  this.hitEndOfResults = false;                      // back-stepping UNLATCHES
  if (this.scrollNextCounter === 1) {                // only one page taken: nothing before it
    this.skip = 0; this.scrollNextCounter = 0;
    return [];
  }
  this.skip = Math.max(this.skip - this.limit * 2, 0);
  if (this.skip === 0) { this.scrollNextCounter = 0; }
  return this.fetch();
}
```

**Flow:** forward: empty page ⇒ latch ⇒ every later `scrollNext()` short-circuits to `[]` WITHOUT a network call. backward: unlatch first, then jump back TWO limits (one for the page you're on, one for the one before) and refetch — that's why scrollBack after N forwards lands on page N−1 with fresh data. The `scrollNextCounter === 1` special case answers "back from page one" as an honest empty array instead of refetching the same page.
**Invariant:** the latch must be cleared on ANY rewind (`hitEndOfResults = false` precedes everything in scrollBack); skip never goes negative (`Math.max(..., 0)`), and hitting 0 resets the counter so a later scrollBack-from-start stays consistent. `restart()` resets skip but NOT the latch or counter (:55–58 — quirk: restart leaves hitEndOfResults set, recorded here so a porter doesn't inherit it blindly).
**Probe:** `test/search/search-repository.spec.ts:126–207` (three sequential scrollNext calls stub start=0/10/20; skip=100/limit=1 override scrolls 100→101→102; scrollBack after two forwards refetches start=0) + invitation twin default `limit: 100` (`invitation.repository.ts:43–57`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "SkipLimitScroller hitEndOfResults", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: empty-page latch + two-limit rewind + counter-based "no previous page" answer — the minimal correct state machine for offset pagination against flaky collection APIs. Adapt defaults (limit 10 vs 100). Omit the restart() latch leak (fix it in your port; noted as upstream quirk). Direct tests pin the full matrix.
