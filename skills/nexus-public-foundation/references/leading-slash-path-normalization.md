<!-- capsule-v2 -->
# Leading-slash path normalization — how do you make path regexes written for "/foo/bar" also match "foo/bar", safely, inside stored expressions?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d`; Codebase Memory `nexus-public`. **Question:** How do you normalize user-authored path patterns between slash conventions without a real regex parser, and what happens when you can't?

## Hand-rolled clause-tracking rewriter + reflective AST literal patcher
**Path/Symbol:** `public/common/components/nexus-selector/src/main/java/org/sonatype/nexus/selector/LeadingSlashRegexTransformer.java:transformGroup,transformLeadingSlash` (:43–276); `LeadingSlashScriptTransformer.java:trimLeadingSlashes,transformPathLiteral,discoverSetLiteralMethod` (:30–112).
**Signature:** `static String trimLeadingSlashes(final String regex)`; `static ASTJexlScript trimLeadingSlashes(final ASTJexlScript script)`.
**Data Shape:** in: raw regex text or parsed script; out: rewritten text/script, or the ORIGINAL unchanged when no rewrite applies (or when reflection is unavailable); single-use instances.

### Decisive source
```java
private void transformLeadingSlash(final boolean hasPrecedingWildcard) {
  if (hasChar() && (peekNextChar() == '?' || peekNextChar() == '*')) {
    return;                                   // "/?"/"/*" already optional — leave alone
  }
  if (buf == null) { buf = new StringBuilder(regex.length() + 16); }
  buf.append(regex, mark, cursor - 1);
  if (hasPrecedingWildcard || (hasChar() && peekNextChar() == '+')) {
    buf.append("(^|/)");                      // ".*/foo/" -> ".*(^|/)foo/"
  }                                           // else drop it: "/foo/.*" -> "foo/.*"
  mark = cursor;
}

// Script-level: rewrite only `path == "<literal>"` nodes, reflectively
private static final String PATH = "path";
private final Method setLiteralMethod = discoverSetLiteralMethod();   // may be null!

public static ASTJexlScript trimLeadingSlashes(final ASTJexlScript script) {
  if (INSTANCE.setLiteralMethod != null) {
    script.childrenAccept(INSTANCE, null);
  }
  return script;
}
catch (Exception | LinkageError e) {
  log.warn("Cannot replace leading slash in path selector {} with {}", path, transformedPath, e);
}
```

**Flow:** enabled only via `JexlEngine.buildExpression(expr, true)` → script transformer visits two-child comparison nodes, detects `path` identifier against a string literal in either operand position → runs the literal through the regex transformer, whose group walker tracks per-clause state (`hasLeadingText`, `hasWildcard`, alternation resets, nested groups, lookarounds `(?!…)`, char ranges) and rewrites leading slashes: bare leading `/` dropped, wildcard-preceded or `+`-followed `/` becomes `(^|/)` → changed literals patched back into the shared AST via reflective `setLiteral`.
**Invariant:** fail-open-to-original everywhere — unknown constructs return the input untouched, and missing reflective access degrades to a warning instead of breaking evaluation; rewrites never touch slashes that are already optional or mid-clause.
**Probe:** `public/common/components/nexus-selector/src/test/java/org/sonatype/nexus/selector/LeadingSlashRegexTransformerTest.expectedLeadingSlashTransformations` (:26–40) pins 11 exact cases incl. `"/com|/org" → "com|org"`, `"(?!.*/struts/.*).*/apache/.*"` lookaround case, and the nested-range monster (:38–39).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "LeadingSlashRegexTransformer LeadingSlashScriptTransformer trimLeadingSlashes path literal", limit: 10 });
```
Live result (2026-08-26): 730 total hits; top rows = both `trimLeadingSlashes` methods (:45–50 / :59–61), `transformPathLiteral` (:87–98), `discoverSetLiteralMethod` (:100–111), `doVisit` two-child dispatch (:56–79).

## Verdict
Adopt the bounded-subset philosophy: detect leading slashes only in a simple clause grammar and return the original otherwise — correctness over coverage. Adopt `(^|/)` as the wildcard-boundary repair. Adapt which node shapes count as "path comparisons" in your own AST. Omit the reflective `setLiteral` mutation entirely by rebuilding the expression string from transformed literals instead — that fragility (and its graceful-degradation warning) exists only because Nexus patches a third-party AST in place. CRITICAL WIRING NOTE (source-verified): production currently calls `SelectorFactory.createSelector`, which passes `shouldTrimLeadingSlash=false` — this whole mechanism ships tested but dormant at its single call site; flipping the flag is the integration point.
