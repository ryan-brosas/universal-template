<!-- capsule-v2 -->
# CSEL AST whitelist — how do you constrain a general expression language down to a safe, translatable subset?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d`; Codebase Memory `nexus-public`. **Question:** How do you guarantee an expression grammar stays small enough to translate to another target (SQL) without chasing arbitrary language features?

## Deny-by-default visitor over the parsed script
**Path/Symbol:** `public/common/components/nexus-selector/src/main/java/org/sonatype/nexus/selector/CselValidator.java:validateCselExpression,doVisit,visit(ASTERNode),visit(ASTIdentifier)` (:40–159).
**Signature:** `static void validateCselExpression(final ASTJexlScript script)`; visitor overrides return per-node or throw `JexlException`.
**Data Shape:** in: parsed JEXL script; out: void (valid) — any non-whitelisted node ⇒ `JexlException` with a user-readable message.

### Decisive source
```java
private static final Set<String> VALID_IDENTIFIERS = ImmutableSet.of("format", "path");

protected Object doVisit(final JexlNode node, final Object data) {
  throw new JexlException(node, "Expression not supported in CSEL selector");   // DEFAULT = reject
}

protected Object visit(final ASTERNode node, final Object data) {               // a =~ "regex"
  try {
    Pattern.compile(node.jjtGetChild(1).toString());                            // regex compiled NOW, not at query time
    return node.childrenAccept(this, data);
  }
  catch (PatternSyntaxException e) {
    throw new JexlException(node, e.getDescription());
  }
}

protected Object visit(final ASTStringLiteral node, final Object data) {
  String literal = node.getLiteral();
  if (!literal.contains("\"") && !literal.contains("'")) {                      // no embedded quotes
    return node.childrenAccept(this, data);
  }
  throw new JexlException(node, format(EMBEDDED_STRING_MESSAGE, literal));
}

protected Object visit(final ASTIdentifier node, final Object data) {
  String id = node.getName();
  if (VALID_IDENTIFIERS.contains(id)) return node.childrenAccept(this, data);
  throw new JexlException(node, format(BAD_IDENTIFIER_MESSAGE, id));
}
```

**Flow:** factory parses the csel expression → singleton validator walks the tree via `script.childrenAccept(INSTANCE, null)` → explicitly overridden visits (`||`, `&&`, `==`, `!=`, `=~` with compile-check, `=^`, parens, quote-free string literals, whitelisted identifiers) recurse into children → any other node type (arithmetic, method calls, ternaries, local vars, `coordinate.*`) hits `doVisit` and throws.
**Invariant:** the accepted language is exactly the set of node types with explicit visit overrides plus nothing — adding a new operator to the translator REQUIRES adding its whitelist entry, keeping grammar and SQL translation in lockstep; regex validity is checked at validation time so bad patterns can never reach evaluation or translation.
**Probe:** `public/common/components/nexus-selector/src/test/java/org/sonatype/nexus/selector/CselValidatorTest.java` — `parsesAllValidContentSelectors` (:39–44, fixture `validJexlContentSelectors.json`); `failsToParseCoordinateContentSelectors` (:51–54) `coordinate.groupId == "com.sonatype"` ⇒ JexlException; `failsToValidateEmbeddedSingleQuoteInStrings` / `_DoubleQuote` (:61–69); `failsToValidateInvalidRegex` (:71–74) `path =~ '*foo*'`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "CselValidator validateCselExpression valid identifiers format path whitelist visitor", limit: 10 });
```
Live result (2026-08-26): 1,525 total hits; top rows = `VALID_IDENTIFIERS` field (:45–45), `validateCselExpression` (:57–59), `doVisit` deny default (:65–68), identifier `visit` (:149–158).

## Verdict
Adopt the deny-by-default visitor as THE grammar definition — it doubles as documentation of what translates. Adapt the identifier whitelist and operator set to your domain fields. Omit the embedded-quote ban if your translator escapes literals instead (Nexus bans them because its SQL builder binds raw literal text as parameters). Keep regex pre-compilation at validation time regardless.
