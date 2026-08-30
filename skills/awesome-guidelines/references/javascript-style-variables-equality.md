<!-- capsule-v2 -->
# Variables and equality — are bindings and comparisons footgun-free?

**Source:** Google jsguide §5.1, §5.10; Airbnb §Variables, §Comparison. **Question:** Will hoisting/var or loose equality cause silent bugs?

## Declaration seam
**Path/Symbol:** local bindings in functions/modules.
**Signature:** `const` default; `let` for reassignment; one binding per declaration.
**Data Shape:** declare at first use, not block-top ritual.

### Decisive rules
```javascript
const items = [];
let active = true;

if (value == null) {
  // null OR undefined only — intentional exception to ===
}

if (name !== '') { ... }
if (users.length > 0) { ... }
```

**Flow:** choose `const` → escalate to `let` only when reassigned → never `var` → compare with `===` except documented `== null`.
**Invariant:** `var` is banned; boolean checks use truthiness; string/number emptiness uses explicit comparisons when `0`/`''` are valid values.
**Probe:** eslint `no-var`, `prefer-const`, `eqeqeq` (with `null` option if configured); no `if (x === true)`.

## Truthiness seam
**Flow:** objects/arrays always truthy → don't use `if (arr)` when empty array matters → prefer `arr.length > 0` or explicit null checks for API boundaries.
**Invariant:** `== null` is the only routine loose equality; not a license for `== 0` or `== ''`.
**Probe:** review catches `if (collection.length)` when length 0 is meaningful; TypeScript strict checks align on public APIs.

## Verdict
Adopt const/let + === with nullish exception + explicit string/count checks. Learning note: `javascript-style-learning-note.md`.
