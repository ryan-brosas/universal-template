<!-- capsule-v2 -->
# BOM-slicing fix sweep — how do you apply a sorted batch of non-overlapping text edits to a string that may start with a BOM?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How does applyFixes turn sorted `{range,text}` commands into one output string, and what are the exact rejection rules?

## SourceCodeFixer.applyFixes sweep
**Path/Symbol:** `lib/linter/source-code-fixer.js:SourceCodeFixer.applyFixes` (:61–152) + `attemptFix(problem)` (:86–110) + `compareMessagesByFixRange` (:26–28) + `compareMessagesByLocation` (:37–39).
**Signature:** `applyFixes(sourceText, messages, shouldFix?): { fixed:boolean, messages:Message[], output:string }`.
**Data Shape:** `shouldFix` may be `false`, `undefined/true` (fix all), or a per-message PREDICATE; messages without an own truthy `fix` property (`Object.hasOwn` gate) bypass the sweep entirely and land in remainingMessages unchanged; BOM (`\uFEFF`) is detected with `startsWith` and sliced off BEFORE offsets apply.

### Decisive source
```js
let lastPos = Number.NEGATIVE_INFINITY, output = bom;
function attemptFix(problem) {
  const start = problem.fix.range[0], end = problem.fix.range[1];
  if (lastPos >= start || start > end) {          // overlap OR reversed range
    remainingMessages.push(problem); return false;
  }
  if ((start < 0 && end >= 0) || (start === 0 && problem.fix.text.startsWith(BOM))) output = "";
  output += text.slice(Math.max(0, lastPos), Math.max(0, start)) + problem.fix.text;
  lastPos = end; return true;
}
// fixes.sort(compareMessagesByFixRange) — by range[0] then range[1]
// after loop: output += text.slice(Math.max(0, lastPos));
// returned unfixed messages re-sorted by compareMessagesByLocation (line then column)
```

**Flow:** partition (has-own-truthy-fix vs not) → sort fixables by range → single forward sweep emitting untouched source up to each accepted fix's start, splicing its text, advancing lastPos past its end → conflicts/reversed ranges fall back to remainingMessages → append tail.
**Invariant:** ONE pass applies only mutually non-overlapping fixes in range order; an overlapped fix is DEFERRED (not merged), and `fixed:true` is set whenever any attempt was made even if it conflicted — so outer loops re-verify and can retry deferred fixes next pass. Negative-range fixes starting at `-1` are the BOM-removal idiom: `(start<0 && end>=0)` clears the already-emitted BOM from `output`. `lastPos = Number.NEGATIVE_INFINITY` (not 0) is load-bearing: `Math.max(0, lastPos)` still emits from 0 while letting the first comparison succeed. A shouldFix predicate returning false pushes to remainingMessages WITHOUT consuming its position in the sweep.
**Probe:** `tests/lib/linter/source-code-fixer.js` (:430 only-one-of-overlapping-applied; :445–447 end==start adjacency IS applied; :477 order-independent conflict outcome; :519–562 BOM insert/remove/replace matrix incl. negative ranges; :565–586 nullish fixes never throw; :156–249 shouldFix-predicate matrix).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "SourceCodeFixer applyFixes attemptFix compareMessagesByFixRange", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.linter.source-code-fixer.SourceCodeFixer.applyFixes" });
```

## Verdict
Adopt the sort-once/sweep-once design, the NEGATIVE_INFINITY sentinel, BOM slicing, and defer-don't-merge conflict semantics verbatim — they encode ten years of regression fixes; adapt the message-shape coupling away if your engine separates edits from diagnostics.
