<!-- capsule-v2 -->
# CreatedBeforeScroller — timestamp-keyed pagination with a scroll-back stack (how do I page a feed backwards by cursor AND re-read forward)?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** How do I page a newest-first timeline (messages, conversations) by "created before" cursor while still supporting deterministic back-navigation to earlier pages?

## The abstract scroller
**Path/Symbol:** `src/scrollers/created-before-scroller.ts:CreatedBeforeScroller` (:3–47).
**Signature:** `abstract class CreatedBeforeScroller<T> { abstract fieldName: keyof T; abstract fetch(): Promise<T[]>; scrollNext(): Promise<T[]>; scrollBack(): Promise<T[]>; restart(): void }`.
**Data Shape:** `createdBefore?: number` (ms epoch, the live cursor), private `prevCreatedBefore?` and `pageIndexes: number[]` (the back-stack of prior cursors).

### Decisive source
```ts
async scrollNext(): Promise<T[]> {
  const results = await this.fetch();
  if (this.prevCreatedBefore) { this.pageIndexes.push(this.prevCreatedBefore); }
  if (!isEmpty(results)) {
    this.prevCreatedBefore = this.createdBefore || ((results[0][this.fieldName] as unknown as number) + 1000);
    this.createdBefore = (results[results.length - 1][this.fieldName] as unknown as number);
  }
  return results;
}
async scrollBack(): Promise<T[]> {
  if (isEmpty(this.pageIndexes)) { return []; }
  this.createdBefore = this.pageIndexes.pop();
  return this.fetch();
}
```

**Flow:** fetch → stash the PREVIOUS page's cursor on the stack → advance `createdBefore` to the LAST item's timestamp (`results[len-1][fieldName]`) — newest-first order makes the last element the oldest. Empty page = cursor untouched (repeat calls are idempotent). First page with no preset cursor seeds `prevCreatedBefore` from the first result +1000 so scrolling back can return exactly page one.
**Invariant:** the +1000 seed is load-bearing — the API treats `createdBefore` as exclusive-ish; without it the first page would not be refetchable. `scrollBack` pops the stack LIFO: two consecutive backs land on page N−1 then N−2 (pinned by test at :228–229: fourth==second, fifth==first). Back past the start returns `[]` loudly instead of erroring. Subclass supplies only `fieldName` ('createdAt' for MessageScroller, 'lastActivityAt' for ConversationScroller) and a fetch closure — zero endpoint coupling.
**Probe:** `test/message/message-repository.spec.ts:200–249` (three pages forward, two backs reproduce exact earlier pages via per-cursor axios stubs) + :250–259 ("return empty array if trying to scroll back from the starting point"); conversation twin `test/conversation/conversation-repository.spec.ts` (:231–252 same matrix over lastActivityAt).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "CreatedBeforeScroller scrollNext", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern verbatim for ANY newest-first keyed feed (timestamps, sequence numbers, composite cursors): cursor = last-seen key, stack = history, empty-page = no-op. Adapt the +1000 seed margin and field name per source. Omit nothing. Direct tests pin both directions — rare for scraper repos.
