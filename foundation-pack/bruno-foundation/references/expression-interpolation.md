<!-- capsule-v2 -->
# Expression interpolation engine — compile-cached template literals with literal short-circuits and safe-integer guards

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** How do you turn user-authored strings like `{{url}}` / `res.data.pets.map(p => p.name)` into evaluated values without eval-ing the world or mangling big numbers?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-js/src/utils.js:compileJsExpression` (:27-53), `evaluateJsExpression` (:57-63), `evaluateJsTemplateLiteral` (:65-104), `internalExpressionCache` (:55); consumers interpolate vars/headers/body across app+cli.
**Signature:** `evaluateJsTemplateLiteral(templateLiteral: string, context) → any; evaluateJsExpression(expression, context) → any`.
**Data Shape:** context = plain object of in-scope variables; expression cache is an unbounded module Map keyed by raw expression string (compilation is expensive, evaluation cheap).

### Decisive source
```js
const matches = expr.match(/([\w.$]+)/g) ?? [];
const vars = new Set(
  matches
    .filter((match) => /^[a-zA-Z$_]/.test(match))     // starts with valid js identifier
    .map((match) => match.split('.')[0])              // top level identifier (foo)
    .filter((name) => !JS_KEYWORDS.includes(name))    // exclude js keywords
);
const globals = [...vars].filter((name) => name in globalThis);
const body = `let { ${code.vars} } = ${param}; ${code.globals}; return ${expr}`;
return new Function(param, body);
```

**Flow (templateLiteral ladder, order IS contract):** empty/non-string ⇒ returned as-is → trim → EXACT literals `'true'/'false'/'null'/'undefined'` become their JS values → fully double/single-quoted strings unquote → pure numeric becomes Number UNLESS > `Number.MAX_SAFE_INTEGER` (issue #1000: huge ids arrive as strings and must STAY strings) → else wrap in backticks and evaluate as a real template literal with context destructuring.
**Invariant:** variable extraction is dotted-token + keyword-filtered so `Math.max(...)` resolves via the `name = name ?? globalThis.name` shim instead of becoming an undefined destructure; compilation happens ONCE per distinct expression (Map cache) — recompiling per request is the naive-port performance trap; literal ladder must run BEFORE backtick wrapping or `"123"` strings get number-coerced.
**Probe:** `packages/bruno-js/tests/utils.spec.js` :27-56 — pins expression evaluation (`res.data.pets[0].toUpperCase()`), error-on-missing-var, and template-literal behavior.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "evaluateJsTemplateLiteral compileJsExpression", limit: 5 });
```

## Verdict
Adopt compile-cache + destructure-body synthesis + the full literal short-circuit ladder incl. MAX_SAFE_INTEGER guard. Adapt keyword list to your runtime realm; omit jsonQuery/@usebruno/query response parser. Coverage caveat: none — clean coverage at pin.
