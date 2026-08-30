<!-- capsule-v2 -->
# CSEL→SQL translation — how do you compile user expressions into WHERE fragments without SQL injection and without changing their meaning?

**Source:** Nexus Repository EPL-1.0 `main@0a8a425d`; Codebase Memory `nexus-public`. **Question:** How do you translate a whitelisted expression AST into a parameterized SQL predicate while repairing JEXL-vs-SQL semantic differences?

## Parameterizing visitor + prefix/alias builder
**Path/Symbol:** `public/common/components/nexus-selector/src/main/java/org/sonatype/nexus/selector/internal/DatastoreCselToSql.java:transformCselToSql,visit(ASTSWNode),visit(ASTNENode),transformMatchesOperator` (:43–230); `SelectorSqlBuilder.java:appendProperty,appendLiteral,appendExpression` (:27–141).
**Signature:** `void transformCselToSql(final ASTJexlScript script, final SelectorSqlBuilder builder)`; `String getQueryString()` + `Map<String,String> getQueryParameters()`.
**Data Shape:** out: SQL text with `:param_N` placeholders + ordered parameter map; `@Qualifier("mybatis")` component is the default `CselToSql<SelectorSqlBuilder>` binding.

### Decisive source
```java
// SelectorSqlBuilder — the injection wall
public void appendProperty(final String property) {
  queryBuilder.append(propertyAliases.computeIfAbsent(property, p -> {
    checkArgument(isAlphanumeric(p));            // identifiers: alphanumeric or explicitly aliased
    return propertyPrefix + p;
  }));
}
public void appendLiteral(final String literal) {          // literals NEVER inlined
  String parameter = parameterNamePrefix + queryParameters.size();
  queryBuilder.append(parameterPrefix).append(parameter).append(parameterSuffix);
  queryParameters.put(parameter, literal);
}

// DatastoreCselToSql — semantic repairs
protected Object visit(final ASTNENode node, final Object data) {   // a != b
  ...
  transformNotEqualsOperator(leftChild, (ASTStringLiteral) rightChild, (SelectorSqlBuilder) data);
}
private SelectorSqlBuilder transformNotEqualsOperator(...) {
  builder.appendExpression(() -> {
    node.jjtAccept(this, builder);
    builder.appendOperator("is null or");        // SQL NULL != x is NULL, but JEXL null != x is true:
    node.jjtAccept(this, builder);               // emit (a is null or a <> b)
    builder.appendOperator("<>");
    literal.jjtAccept(this, builder);
  });
}

if (pattern.charAt(0) != '^') {
  pattern = "^(" + pattern + ")$";               // =~ must match ENTIRE string like JEXL, anchor it
}
builder.appendLiteral(pattern);

builder.appendOperator("like");
builder.appendLiteral(literal.getLiteral() + '%'); // =^ becomes prefix LIKE
```

**Flow:** `CselSelector.toSql` hands the stored syntax tree to the visitor → operators recurse left/op/right (`|| → or`, `&& → and`, `== → =`, `=~ → ~`, `!= → (a is null or a <> :p)`) → parens re-emit through `appendExpression` to preserve precedence → identifiers become aliased/prefixed property names (dotted `format.attr` contributes its attribute name) → every string literal becomes a numbered bind parameter.
**Invariant:** user text can only enter the query as a *bound value* (property names are alphanumeric-checked against an alias map), so injection has no channel; translated predicates must be semantically equal to JEXL evaluation — hence null-safe `!=` and full-string anchoring of `=~` patterns that lack `^`.
**Probe:** `public/common/components/nexus-selector/src/test/java/org/sonatype/nexus/selector/internal/DatastoreCselToSqlTest.java` — `notEqualTest` (:88–96) ⇒ `(a_alias is null or a_alias <> :param_0)`; `regexpTest` (:122–154): `woof → ^(woof)$`, `^woof → ^woof` unchanged, `^/woof|/woof/foo` untouched; `likeTest` (:77–85) ⇒ param `woof%`; `andTest` (:53–62) exact alias/param wiring; `publicDocumentationExampleTest` (:157–178).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nexus-public", query: "DatastoreCselToSql SelectorSqlBuilder appendLiteral appendProperty transformCselToSql parameterized", limit: 10 });
```
Live result (2026-08-26): 33 total hits; top rows = `appendProperty` (:86–91), `appendLiteral` (:96–100), `transformCselToSql` (:52–55), plus consumer `CselToExpression` in nexus-search-sql (:60–63).

## Verdict
Adopt the two-part shape: a dumb builder that owns escaping policy (bind-everything, alphanumeric-only identifiers) and a visitor that owns grammar-to-target mapping plus explicit semantic repairs. Adapt prefixes/aliases (`prop.`, `:param_`) and the regex dialect marker (`~` operator) to your datastore. Omit the `clearQueryString` reuse path unless you rebuild many queries with one configured builder.
