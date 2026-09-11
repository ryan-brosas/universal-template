<!-- capsule-v2 -->
# Modules and exports — is the public surface stable and named?

**Source:** Google jsguide §3.4; Airbnb §Modules. **Question:** Can consumers import symbols consistently without default-export naming drift?

## Export seam
**Path/Symbol:** ES module `export` / `import`.
**Signature:** named exports only; no exported `let` mutations.
**Data Shape:** `export {Foo};` or `export class Foo`.

### Decisive contrast
```javascript
// Wrong — default export naming varies per importer
export default class UserService {}

// Right — stable symbol names
export class UserService {}

// Wrong — mutable export binding
export let requestCount = 0;

// Right — module-private state + accessor
let requestCount = 0;
export function getRequestCount() {
  return requestCount;
}
```

**Flow:** define module-local symbols → export only API surface → aggregate imports from same path once → avoid duplicate import lines.
**Invariant:** exported bindings are **immutable references**; mutation happens via functions or object fields behind a constant export.
**Probe:** eslint `import/no-mutable-exports`; grep `export default` absent in app code (unless project documents Airbnb exception).

## Import seam
```javascript
import {UserService} from './user-service.js';
import * as stringLib from './lib/string.js';
```

**Flow:** prefer named imports keeping original names → use `import * as` for collisions → include extension when project requires (Google `.js`).
**Invariant:** do not import the same file twice with fragmented bindings.
**Probe:** `no-duplicate-imports` clean; import graph resolves without ambiguous bare paths.

## Verdict
Adopt named exports and non-mutable module API; project picks default-export exception explicitly if needed. Learning note: `javascript-style-learning-note.md`.
