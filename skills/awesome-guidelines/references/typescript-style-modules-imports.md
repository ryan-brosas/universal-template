<!-- capsule-v2 -->
# Modules and imports — is the module graph ES-native and type-clean?

**Source:** Google tsguide §Imports/Exports; handbook modules. **Question:** Are symbols imported/exported with stable names and correct type/value separation?

## Export seam
**Path/Symbol:** ES module `export` / `import`.
**Signature:** named exports only; no `export let`; no default exports; no namespace blocks.
**Data Shape:** `export class Foo {}`, `export type {Bar}`, `export function baz()`.

### Decisive contrast
```typescript
// Wrong — default export naming drift
export default class UserService {}

// Right — stable named symbol
export class UserService {}

// Wrong — mutable export binding
export let requestCount = 0;

// Right — module-private state + accessor
let requestCount = 0;
export function getRequestCount(): number {
  return requestCount;
}

// Wrong — container class for namespacing
export class Container {
  static FOO = 1;
  static bar() { return 1; }
}

// Right — file-scope exports
export const FOO = 1;
export function bar(): number { return 1; }
```

**Flow:** define module-local symbols → export only public API → dedupe imports from same path → use `import type` when value unused.
**Invariant:** exported bindings are **immutable references**; no `namespace`, `require`, or `/// <reference>`.
**Probe:** grep `export default` absent in app code; eslint `import/no-mutable-exports`; no `namespace` / `import = require`.

## Import seam
```typescript
import {UserService} from './user-service';
import * as tableview from './tableview';
import type {Options} from './options';
import {type Foo, Bar} from './foo';
```

**Flow:** relative paths within project → named imports for frequent symbols → `import * as` for large APIs/collisions → side-effect imports only for polyfills/custom elements.
**Invariant:** type-only symbols use `import type` (or inline `type` import); re-export types with `export type`.
**Probe:** `tsc --importsNotUsedAsValues` / `verbatimModuleSyntax` clean; no duplicate import lines from same path.

## Verdict
Adopt Google module discipline: named exports, non-mutable surface, ES modules only. Learning note: `typescript-style-learning-note.md`.
