<!-- capsule-v2 -->
# TokenStore cursor navigation — how do skip / count / filter / includeComments compose when enumerating tokens around AST nodes?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f`; Codebase Memory project `eslint`. **Question:** When porting token enumeration (getFirstToken/getTokensBetween-style APIs), how do the option forms and decorator layers actually order, filter, and cap the stream?

## Options normalization + cursor decoration
**Path/Symbol:** `lib/languages/js/source-code/token-store/index.js:createCursorWithSkip` (:89–128), `createCursorWithCount` (:145–187), `createCursorWithPadding` (:216–257); `token-store/cursors.js:CursorFactory.createCursor` (:76–107).
**Signature:** `createCursorWithSkip(factory,…,opts)` where opts is number→skip, function→filter, or {includeComments, skip, filter}; `createCursorWithCount` identical shape with count.
**Data Shape:** every public method funnels here; iteration windows are half-open location pairs built from node ranges (`[left.range[1], right.range[0])` between two nodes, `[-1, node.range[0])` before, `[node.range[1], -1)` after).

### Decisive source
```js
// cursors.js — decoration ORDER is the contract:
let cursor = this.createBaseCursor(...);        // direction + includeComments
if (filter)      cursor = new FilterCursor(cursor, filter);
if (skip >= 1)   cursor = new SkipCursor(cursor, skip);   // skip counts POST-filter tokens
if (count >= 0)  cursor = new LimitCursor(cursor, count); // count===0 iterates NOTHING;
                                                          // absent count arrives as -1 = unlimited
// index.js createCursorWithCount tracks countExists separately from count value:
countExists = typeof opts.count === "number";   // 0 is meaningful, undefined is not
assert(skip >= 0, "options.skip should be zero or a positive integer.");
```

**Flow:** normalize opts → pick base cursor by DIRECTION factory (forward/backward) × includeComments (Token vs TokenComment cursor) → wrap Filter → Skip → Limit → consume via getOneToken()/getAllTokens(). Backward-producing methods call `.reverse()` on the collected array to restore document order. Numeric padding args route to PaddedTokenCursor which clamps `index -= beforeCount`/`indexEnd += afterCount` to array bounds.
**Invariant:** skip counts tokens that already PASSED the filter (Limit(Skip(Filter(base))) chain); `{count:0}` yields an empty array while omitted count yields everything — conflating them silently returns nothing. Between-windows are exclusive of BOTH endpoints, so adjacent nodes give []. getCommentsBefore/After iterate a comment-inclusive cursor and collect only the ADJACENT RUN until the first non-comment (`getAdjacentCommentTokensFromCursor`, :265–275).
**Probe:** `tests/lib/languages/js/source-code/token-store.js` (:1421–1445 skip-after-filter ladder "=", then filtered "C"; :84–106 padding counts; :1664–1673 padding between nodes). Executed live at pin: full suite 182 passing; probe script reproduced B / "=" / C, padding "answer = a * b ;", adjacency [B].

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "TokenStore createCursorWithSkip createCursorWithCount LimitCursor", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.languages.js.source-code.token-store.TokenStore.getTokensBetween" });
```

## Verdict
Adopt the option-normalization grammar (number/function/object), the filter→skip→limit ordering, the count=0-vs-absent split, exclusive between-windows, and reverse-on-collect for backward reads. Adapt cursor classes to host iterator idioms if desired — but keep skip-post-filter semantics or rule ports that combine filter+skip misalign by one. Omit PaddedTokenCursor only if the host drops positional padding arguments entirely.
