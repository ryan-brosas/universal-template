# TypeScript style — learning note

**Status:** deep ingest (2026-08-29). **Feeds:** `typescript-style-*.md` capsules, `typescript-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Google TypeScript Style Guide](https://google.github.io/styleguide/tsguide.html) | Named exports only; `import type`; ES modules not namespaces; relative imports within project; no default exports; no mutable `export let`; no container classes; `import type` / `export type`; no `#private`; `readonly`; parameter properties; no `const enum`; nullable aliases banned; prefer optional over `\|undefined`; `T[]` over `Array<T>`; `unknown` over `any`; minimal type assertions; `== null` OK |
| [TypeScript handbook — Do's and Don'ts](https://www.typescriptlang.org/docs/handbook/declaration-files/do-s-and-don-ts.html) | Primitives not boxed types; no unused generic params; `any` only during JS migration; `void` not `any` for ignored callback returns; non-optional callback params; single overload with max arity; overload ordering (specific before general); optional params over overload chains; union types over single-arg overloads |
| [basarat/typescript-styleguide](https://github.com/basarat/typescript-styleguide) (secondary) | Aligns with Google on modules, `unknown`, strictness; reinforces eslint/tsc as enforcement |

**Not duplicated here:** Domain modeling, branded types, Effect/Result error modeling — `typescript-coding-standards`. Plain JS module habits — `javascript-coding-practices`.

## Mental model

TypeScript style is **typed JavaScript with explicit module boundaries**:

1. **Modules** — ES `import`/`export` only; named exports; `import type` for type-only symbols; file scope replaces namespaces.
2. **Types** — primitives lowercase; ban `any` in finished code; `unknown` + narrow at boundaries; no nullable type aliases; optional params over overload sprawl.
3. **Classes** — prefer functions + file scope over static containers; `readonly` + parameter properties; TS `private` not `#`; no `const enum`.
4. **Interop** — respect JS null vs undefined conventions per API; `== null` for nullish checks; assertions sparingly with `as`, never angle-bracket form.

## Decision tables

### Modules & exports

| Topic | Google | Handbook | Catalog default |
|---|---|---|---|
| Default export | **banned** | — | named exports only |
| Namespace / `require` | **banned** | — | separate files |
| Mutable export | forbidden | — | getter functions |
| Container class | forbidden | — | module-level const/fn |
| Import path | relative within project | — | limit `../../../` depth |
| Type-only import | `import type` | — | required when value unused |

### Types & nullability

| Case | Rule |
|---|---|
| Unknown input | `unknown` then narrow; not `any` |
| Boxed types | never `String`, `Number`, `Boolean`, `Object` |
| Nullable alias | `type Foo = Bar \| null` **banned** — add null at use site |
| Optional param | prefer `foo?: T` over `foo: T \| undefined` |
| Absent value | match host API (`undefined` vs `null`) |
| Enum in boolean | never — compare to named member |
| Assertions | `as` syntax; avoid unless obvious; no `!` unless documented |

### Callbacks & overloads (handbook)

| Case | Rule |
|---|---|
| Ignored callback return | `() => void` not `() => any` |
| Callback arity | non-optional params; callee may ignore extras |
| Overload ordering | most specific signature first |
| Trailing-param overloads | collapse to optional parameters |
| Single-arg type overloads | use union type |

### Classes & members

| Topic | Rule |
|---|---|
| `#private` fields | banned — use `private` |
| `const enum` | banned — plain `enum` |
| Parameter properties | preferred over manual assign in ctor |
| `public` modifier | omit except non-readonly parameter properties |
| Static `this` | banned |
| Class declaration | no trailing semicolon; expression class needs `;` |

## Anti-patterns

- `export default class Foo`
- `export let counter = 0`
- `namespace Foo { ... }` or `import x = require('...')`
- `type Response = Data | null` exported and reused everywhere
- `function fn(x: () => any)` for fire-and-forget callbacks
- `catch (e: any)` — use `unknown`
- `const enum Status` — breaks downstream consumers
- `#ident` private fields when targeting pre-ES2015 emit

## Skill trace

| Artifact | Role |
|---|---|
| `typescript-style-modules-imports.md` | import/export, import type, paths |
| `typescript-style-types-nullability.md` | any/unknown, nullability, callbacks |
| `typescript-style-classes-api.md` | classes, readonly, enums, assertions |
| `typescript-style-verify.md` | tsc/eslint probes |
| `typescript-coding-practices` | application skill |
| `typescript-coding-standards` | domain architecture (parallel, not replaced) |
