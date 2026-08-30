<!-- capsule-v2 -->
# No-loss-of-precision zero-underflow gate — when is a nonzero-written literal that evaluates to 0 an error rather than a valid zero?

**Source:** ESLint MIT `main@c27bc926e496985eb7911c09eb60914b2e4b5d0f` (#21218); Codebase Memory project `mnt-hdd-utopia-inspo-frameworks-eslint` (path-slugged twin; stuck short-name `eslint` serves the pre-drift graph). **Question:** `5e-324` (valid) and `1e-324` (invalid) both have `node.value === 0` — what distinguishes a legitimate zero from a precision loss, and why did the old falsiness gate miss the entire underflow family?

## baseTenLosesPrecision zero branch + Literal gate
**Path/Symbol:** `lib/rules/no-loss-of-precision.js:baseTenLosesPrecision` (:180–206; zero branch :187–189) and the listener gate at :244 (`isNumber(node) && losesPrecision(node)`).
**Signature:** `baseTenLosesPrecision(node: Literal) -> boolean` via `losesPrecision` → `isBaseTen` ternary (:213–217); listener `Literal(node)` on every numeric literal.
**Data Shape:** input is the raw AST Literal (`raw` string, `value` number); internal state is a `ScientificNotation {coefficient: string, magnitude: number}` produced by `convertNumberToScientificNotation(raw, parseAsFloat=false)` — coefficient digits with implied decimal after the first digit.

### Decisive source
```js
const normalizedRawNumber = convertNumberToScientificNotation(rawNumber, false);

if (node.value === 0) {
    return !/^0+$/u.test(normalizedRawNumber.coefficient);
}

const requestedPrecision = normalizedRawNumber.coefficient.length;
if (requestedPrecision > 100) {
    return true;
}
// ... toPrecision round-trip comparison of magnitude+coefficient
```

**Flow:** normalize the raw text → if runtime value is exactly 0, decide SOLELY on the written coefficient (`/^0+$/u`: all-zeros ⇒ legitimate zero ⇒ no loss; any nonzero digit ⇒ user wrote something that underflowed ⇒ report) → otherwise run the legacy requested-precision/toPrecision comparison.
**Invariant:** **falsiness is not zero-testing**: the pre-fix listener gate `node.value && losesPrecision(...)` silently exempted EVERY falsy value — `0`, `-0`, and the entire positive-underflow family (`1e-324`…`1e-350` all flush to `+0`; `-1e-350` to `-0`). The fix has two halves that MUST land together or both regressions appear: dropping `node.value &&` re-admits zeros (harmless only because…), and adding the zero-branch makes those newly-admitted zeros classify correctly. The classifier itself is textual: `5e-324` survives as the minimum subnormal (coefficient "5" but value ≠ 0 → never reaches the zero branch), `1e-324` underflows (coefficient "1", value === 0 → reported), `0e5`/`0008`(octal-invalid)/plain `0` carry all-zero coefficients → valid. Porting trap: `removeLeadingZeros("0")` returns `"0"` unchanged (loop finds no non-zero char), which is what keeps `0e5`'s coefficient `/^0+$/`-clean; and `-1e-350` arrives as unary-minus over a POSITIVE Literal — sign lives outside the node, so classification is magnitude-only by construction. The >100-digit guard stays AFTER the zero branch so pathological zero-ish literals still short-circuit cheaply.
**Probe:** `tests/lib/rules/no-loss-of-precision.js` — new invalid cases `1e-350`/:345, `1e-324`/:349, `-1e-350`/:353; new valid case `5e-324`/:64 (MIN_VALUE must stay legal); regression-valid `0e5`/:63, plain zero. Behaviorally executed from disk: RED at `dc1e7a84` flagged none of I/J/K (all swallowed by the falsiness gate); GREEN at `c27bc92` reports all three while keeping `5e-324`/`0e5`/`0`/big-int cases correct.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-frameworks-eslint", name_pattern: "baseTenLosesPrecision", limit: 10 });
// resolves: ...no-loss-of-precision.baseTenLosesPrecision Function lib/rules/no-loss-of-precision.js 180-206
```

## Verdict
Adopt the two-part pattern for any numeric-literal validator: (a) never gate validation on truthiness of the parsed value — use `typeof value === "number"` / explicit zero checks; (b) when parsed value collapses to 0, fall back to the WRITTEN form to distinguish intended zero from lost precision. Adapt the regex to the host's normalization (any canonical-coefficient representation works as long as all-zero ⇔ intended zero). Omit nothing. Coverage caveat: probes executed via extracted-tree behavioral harness driving the rule file directly with stub literals, not the repo mocha suite (inspo clone has no installed toolchain).
