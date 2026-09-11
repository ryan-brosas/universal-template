<!-- capsule-v2 -->
# Functions and banned features — is `this`, naming, and API surface sane?

**Source:** Google jsguide §5.5, §5.9, §5.11, §6; Airbnb §Functions, §Arrow Functions. **Question:** Are nested callbacks, names, and forbidden constructs under control?

## Functions seam
**Path/Symbol:** functions, methods, arrow callbacks.
**Signature:** `lowerCamelCase` functions; `UpperCamelCase` classes; `CONSTANT_CASE` true constants.
**Data Shape:** arrow functions for nested callbacks; JSDoc/types on exported API.

### Decisive patterns
```javascript
/** @param {string} id @return {Promise<User>} */
export async function fetchUser(id) {
  return api.get(`/users/${id}`);
}

class Cache {
  /** @private {Map<string, User>} */
  store_ = new Map();

  get(key) {
    return this.store_.get(key);
  }
}

items.map((item) => transform(item));
getValue((result) => void notify(result));
```

**Flow:** export documented functions → nested logic uses arrows (not `.bind(this)`) → `this` only in classes/methods/explicit `@this`.
**Invariant:** public identifiers are descriptive ASCII camelCase; short names only in ≤10-line scopes.
**Probe:** no `function(){}` callbacks where arrow fixes `this`; exported functions have JSDoc or TypeScript types.

## Disallowed seam
```javascript
// Never
with (obj) { ... }
eval(userInput);
new String('x');
var legacy = 1;
```

**Flow:** ban `with`/`eval`/non-standard syntax → no primitive wrappers → no builtin prototype patches.
**Invariant:** CSP-safe codebases cannot depend on `eval` or `Function(string)`.
**Probe:** eslint `no-eval`, `no-with`, `no-extend-native`; security review flags dynamic code paths.

## Verdict
Adopt camelCase + arrows for nesting + documented exports; forbid eval/with/var/wrapper objects. Learning note: `javascript-style-learning-note.md`.
