<!-- capsule-v2 -->
# Inline-config comment gate — which comments count as config, and how does SourceCode cache that selection?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f`; Codebase Memory project `eslint`. **Question:** Which comment labels may carry inline configuration, who owns that allowlist, and how is the selection cached for both the disable-directives and applyInlineConfig planes?

## Shared directivesPattern + SourceCode.getInlineConfigNodes
**Path/Symbol:** `lib/shared/directives.js:directivesPattern` (:11–13); `lib/languages/js/source-code/source-code.js:getInlineConfigNodes` (:827–861), `getDisableDirectives` (:870–938), `applyInlineConfig` (:981+).
**Signature:** `getInlineConfigNodes(): Comment[]` — cached under `this[caches]` key `"configNodes"`.
**Data Shape:** allowlist regex `/^(eslint(?:-env|-enable|-disable(?:(?:-next)?-line)?)?|exported|globals?)(?:\s|$)/u` — the label must be followed by whitespace or end of value.

### Decisive source
```js
configNodes = this.ast.comments.filter(comment => {
  if (comment.type === "Shebang") return false;            // shebangs are never directives
  const directive = commentParser.parseDirective(comment.value);
  if (!directive) return false;
  if (!directivesPattern.test(directive.label)) return false;   // shared engine gate
  return comment.type !== "Line" ||
    !!/^eslint-disable-(?:next-)?line$/u.test(directive.label); // Line comments: disable family only
});
this[caches].set("configNodes", configNodes);
```

**Flow:** `getDisableDirectives` and `applyInlineConfig` both call `getInlineConfigNodes` first (cache hit after the first walk) → `getDisableDirectives` re-checks the Line-comment restriction per label, rejects a multi-line `eslint-disable-line` as a problem, and builds `Directive` objects for the four disable-family labels → `applyInlineConfig` switches on label: `exported`/`globals` parse list/string configs, `eslint` parses JSON-like rule config into `{config:{rules}, loc}`, `eslint-env` is a hard "no longer supported" problem.
**Invariant:** the shared pattern is the single engine-internal allowlist — adding a new inline directive label means touching `lib/shared/directives.js`, not each consumer. Line comments are restricted to the disable family because `/* eslint foo: 1 */`-style config needs block scope. The cache is per-SourceCode-instance and computed once. This gate is DISTINCT from the rule-author-facing `isDirectiveComment` predicate (`ast-utils.js`, see directive-recognition-predicates), which has a wider prefix table for a different porting question.
**Probe:** `tests/lib/languages/js/source-code/source-code.js:2202` describe("getInlineConfigNodes()") — exact comment selection incl. non-config exclusion; `:2350` describe("applyInlineConfig()") — globals/exported/eslint handlers. Live probe this pass: `directivesPattern.test` over `["eslint","eslint-disable-next-line","global","globals","exported"]` all true; `"foo"`/`"eslintx"` false (node -e run at the pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "directivesPattern getInlineConfigNodes applyInlineConfig getDisableDirectives", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.languages.js.source-code.source-code.SourceCode.getInlineConfigNodes" });
```

## Verdict
Adopt a single shared allowlist plus a cached node selection for any inline-config plane; adapt the label vocabulary to your host; omit the Shebang special case only if your grammar has no shebang comments. Caveat: Codebase Memory MCP was not connected in the mining session; anchors verified by direct byte-matched source reads at the git-clean pin.
