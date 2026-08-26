<!-- capsule-v2 -->
# Retained-range fix composition — how do multi-edit fixes claim a conflict-free span so sibling fixes can't interleave?

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How does one rule emit a fix that reserves surrounding tokens (or the whole enclosing function) against other fixes in the same pass?

## FixTracker retained spans
**Path/Symbol:** `lib/rules/utils/fix-tracker.js:FixTracker` (:30–123) — `retainRange(range)` (:48), `retainEnclosingFunction(node)` (:61–70), `retainSurroundingTokens(nodeOrToken)` (:78–88), `replaceTextRange(range, text)` (:94–112), `remove(nodeOrToken)` (:120–122).
**Signature:** builder style — `FixTracker.retainX(...).replaceTextRange(r, t)` returns the fixer command.
**Data Shape:** ONE retained range per tracker; final command's range is the UNION `[min(retained[0],range[0]), max(retained[1],range[1])]` and its text re-splices original source OUTSIDE the replaced sub-range: `text.slice(actualStart, rangeStart) + text + text.slice(rangeEnd, actualEnd)`.

### Decisive source
```js
if (this.retainedRange) {
  actualRange = [Math.min(this.retainedRange[0], range[0]),
                 Math.max(this.retainedRange[1], range[1])];
}
return this.fixer.replaceTextRange(actualRange,
  this.sourceCode.text.slice(actualRange[0], range[0]) + text +
  this.sourceCode.text.slice(range[1], actualRange[1]));
```

**Flow:** retain-what-you-touch → compute union → rebuild the full replacement by keeping the retained-but-unreplaced head/tail verbatim → hand the single merged command to the normal fix pipeline (where non-overlap with OTHER rules is enforced).
**Invariant:** the tracker does NOT enforce conflicts itself — it EXPANDS one rule's own fix so that SourceCodeFixer's overlap rejection treats everything inside the retained span as claimed by this rule. A smaller-or-equal retained range is ignored (`min/max` absorb it). Fallbacks are deliberate: no enclosing function ⇒ retain whole program range; missing neighbor token ⇒ use the node itself. This is how control-flow-changing fixes (e.g. prefer-const groupings, no-unused-vars removals) avoid colliding with formatting fixes in the same pass.
**Probe:** `tests/lib/rules/utils/fix-tracker.js` (:54 expand-to-explicit-range; :67 smaller-retained-ignored; :80 unspecified-retained; :96–113 replaceTextRange expansion; :111–126 retainEnclosingFunction incl. program fallback; :142 operator-change case).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "FixTracker retainRange retainEnclosingFunction retainSurroundingTokens", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.rules.utils.fix-tracker.FixTracker.replaceTextRange" });
```

## Verdict
Adopt whenever two subsystems edit the same buffer concurrently-by-pass; adapt the fallback ladder to your AST; omit only if your engine already supports per-fix priority/claim metadata.
