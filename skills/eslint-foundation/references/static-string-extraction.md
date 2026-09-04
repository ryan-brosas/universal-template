<!-- capsule-v2 -->
# Static string value extraction — the Literal/TemplateLiteral ladder behind every "what is this property called?" check

**Source:** ESLint MIT `main@dc1e7a8416937edefe04cf836ee202a6fc03bedd`; Codebase Memory project `eslint`. **Question:** How do you decide that an expression node HAS a known string value — including regex literals, bigints, and cooked templates — without evaluating anything?

## getStaticStringValue
**Path/Symbol:** `lib/rules/utils/ast-utils.js:getStaticStringValue(node)` (:243–270).
**Signature:** `(node) => string|null`.
**Data Shape:** `Literal` branches on what's IN the value slot: null-value Literal is disambiguated (`isNullLiteral` ⇒ "null"; `.regex` ⇒ `/pattern/flags`; `.bigint` ⇒ bigint string; else null); TemplateLiteral qualifies ONLY with zero expressions and a single quasi (returns `.cooked`).

### Decisive source
```js
case "Literal":
  if (node.value === null) {
    if (isNullLiteral(node)) return String(node.value);   // literal null ⇒ "null"
    if (node.regex) return `/${node.regex.pattern}/${node.regex.flags}`;
    if (node.bigint) return node.bigint;
    // otherwise unknown literal → fall through to return null
  } else return String(node.value);
  break;
case "TemplateLiteral":
  if (node.expressions.length === 0 && node.quasis.length === 1)
    return node.quasis[0].value.cooked;
  break;
```

**Flow:** switch on type → value-slot disambiguation → default null.
**Invariant:** this is VALUE-staticness, not syntax: `obj["a-b"]` and `` obj[`a-b`] `` both yield names while `obj[a+b]` does not. Regex literals stringify as their source form so `delete x./foo/`-style keys and regex-key comparisons behave consistently. The bigint branch returns the RAW digits (no trailing n). Cooked-over-raw matters for unicode escape normalization in template keys. Callers must treat null as "dynamic" and bail — never substitute empty string.
**Probe:** `tests/lib/rules/utils/ast-utils.js` (:622 getStaticStringValue describe incl. null/regex/bigint/template cases; :726 getStaticPropertyName twin).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "eslint", query: "getStaticStringValue isNullLiteral TemplateLiteral quasis", limit: 10 });
await mcp.codebase_memory.get_code_snippet({ project: "eslint", qualified_name: "eslint.lib.rules.utils.ast_utils.getStaticStringValue" });
```

## Verdict
Adopt as the canonical staticness gate feeding getStaticPropertyName-style checks; adapt which literal kinds your language supports; never widen it to evaluate expressions.
