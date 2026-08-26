<!-- capsule-v2 -->
# TokenStore location index — how are tokens found from offsets in O(1) and comments in O(log k)?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f`; Codebase Memory project `eslint`. **Question:** How does the store resolve a character offset (or a node boundary) to token indices, and where do comments live in that index?

## Index map + binary-search fallback
**Path/Symbol:** `lib/languages/js/source-code/token-store/index.js:createIndexMap` (:36–72), perf docblock (:281–291), `getTokenByRangeStart` (:315–332), `commentsExistBetween` (:637–644); `token-store/utils.js:getFirstIndex` (:53–84), `getLastIndex` (:93–124), `search` (:18–43).
**Signature:** `createIndexMap(tokens, comments): Object.create(null)`; `getFirstIndex(tokens, indexMap, startLoc): number`; `getLastIndex(...endLoc): number`.
**Data Shape:** map keys are token AND comment range endpoints — `map[range[0]] = i` and `map[range[1]-1] = i`. COMMENT entries store the index of the NEXT TOKEN, not the comment; comments themselves are only reachable through the separate sorted COMMENTS array via binary search.

### Decisive source
```js
// createIndexMap: comments deliberately OUTSIDE the hash map (class docblock):
// "Assuming that comments to be much fewer than tokens, this does not make hash map
//  from token's locations to comments to reduce memory cost. This uses binary-searching."
// utils.getFirstIndex — the ±1 correction algebra:
if (startLoc in indexMap) return indexMap[startLoc];
if (startLoc - 1 in indexMap) {
  const index = indexMap[startLoc - 1];
  const token = tokens[index];
  if (!token) return tokens.length;          // out-of-bounds guard
  if (token.range[0] >= startLoc) return index; // comment-pointer entry: no +1 needed
  return index + 1;
}
if (startLoc === 0) return 0;   // Program with no leading token/comment
return tokens.length;
```

**Flow:** constructor builds the endpoint→token-index map once → direction cursors convert window locations to [indexStart,indexEnd] via getFirstIndex/getLastIndex → TokenComment cursors merge the token slice with `comments.slice(search(comments, loc))`, a lower-bound binary search over comment starts. `getTokenByRangeStart(offset)` fetches via base cursor then re-checks `token.range[0] === offset` so a hit on the NEXT token returns null.
**Invariant:** end keys are stored at `range[1]-1` and looked up as `endLoc` or `endLoc-1` with mirrored −1 correction (`token.range[1] > endLoc ⇒ index-1`) — dropping either correction shifts every between-window by one token when a comment sits at the boundary. `commentsExistBetween(left,right)` is fully-contained semantics: first comment with `.range[0] >= left.range[1]` must also satisfy `.range[1] <= right.range[0]`.
**Probe:** `tests/lib/languages/js/source-code/token-store.js` (:1676–1712 getTokenByRangeStart incl. comment-start null-vs-Block cases; :1834–1846 commentsExistBetween). Executed at pin: suite 182 passing; probe confirmed getTokenByRangeStart(commentStart) null without includeComments and Block with it.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "createIndexMap getFirstIndex getLastIndex search commentsExistBetween", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.languages.js.source-code.token-store.utils.getFirstIndex" });
```

## Verdict
Adopt the one-hash-map-over-token-endpoints design plus sorted-comments binary search for any position→AST-token lookup table; the memory rationale is documented in source and holds wherever comments ≪ tokens. Adapt key encoding if host ranges differ. Omit the adjacency-run helpers here (covered by token-store-cursor-navigation).
