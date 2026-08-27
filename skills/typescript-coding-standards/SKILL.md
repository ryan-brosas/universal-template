---
name: typescript-coding-standards
description: Use when writing, refactoring, or reviewing TypeScript code that needs strong domain modeling, typed errors, schema parsing, safe adapters, test seams, or maintainable module boundaries.
disable-model-invocation: true
---


# TypeScript Coding Standards

## Core Principle

Types describe the domain and errors are data: no `any` (branded primitives, `unknown` + narrow), `Result<T,E>`/`Effect<T,E>` instead of thrown domain errors, pure core with effects at the edges.

## When to Use / NOT

- **Use when:** writing, refactoring, or reviewing TypeScript code that needs strong domain modeling, typed errors, schema parsing, safe adapters, test seams, or maintainable module boundaries.
- **NOT when:** the file has no domain surface to model — a throwaway script with no untrusted input, no external systems, and no shared types; or the code is not TypeScript.

## Workflow

1. Model the domain first: branded primitives (`UserId` not `string`), discriminated unions with `kind` discriminants (Domain Modeling).
2. Decode untrusted input at the edge with schema validation; never let `req.body`, `JSON.parse`, `process.env`, or query strings reach the core (Schema Boundaries).
3. Model errors as data with `_tag`; the return type is the contract, handlers switch on `_tag` (Error Modeling).
4. Keep business logic pure; put I/O at the edges behind adapters that implement domain interfaces (Pure Functions, Adapters).
5. Enforce module boundaries: one concern per module, explicit public exports, no circular deps, minimal index files (Module Boundaries).
6. Check Common Mistakes and Red Flags before shipping.

## Iron Laws

<EXTREMELY-IMPORTANT>
- **No `any`.** Branded primitives, schema boundaries, `unknown` + narrow.
- **Errors as data.** `Result<T, E>` or `Effect<T, E>`. Never `throw new Error(...)` for domain.
- **Pure core, effects at edges.** Business logic takes inputs, returns values.
- **Types describe the domain.** `UserId` not `string`.
- **Test seams over mocking.** Inject dependencies as values.
</EXTREMELY-IMPORTANT>

## Domain Modeling

```ts
// Branded primitives (no runtime cost)
type UserId = string & { readonly __brand: "UserId" }
const UserId = (s: string): UserId => s as UserId

// Discriminated unions
type RequestState<T> =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "success"; data: T }
  | { kind: "error"; error: AppError }
```

Use `kind` for discriminants (not `type` — collides with TS).

## Schema Boundaries

Validate untrusted input at the edge. Inside, trust the types.

```ts
const input = Schema.decodeUnknownSync(UserSchema)(req.body)
// Now `input` is `User`, not `unknown`
```

Never let `req.body`, `JSON.parse`, `process.env`, or query strings reach the core. Decode at the boundary.

## Error Modeling

```ts
class UserNotFound extends Error {
  readonly _tag = "UserNotFound" as const
  constructor(readonly userId: UserId) { super(`User ${userId} not found`) }
}

type GetUser = (id: UserId) => Effect.Effect<User, UserNotFound | DbError>
```

The return type is the contract. Handlers switch on `_tag`.

## Pure Functions

```ts
// Pure: input → output, no I/O
const calculateTotal = (items: Item[]): number =>
  items.reduce((sum, i) => sum + i.price * i.qty, 0)

// Impure: I/O, time, randomness
const fetchUser = (id: UserId): Effect.Effect<User, DbError> =>
  Effect.tryPromise(() => db.query(...))
```

Pure = testable without setup. Impure = testable with `TestLayer` or mock implementation.

## Adapters

External systems get an adapter. Adapter implements a domain interface, hides the external API.

```ts
interface UserRepo {
  findById: (id: UserId) => Effect.Effect<User, UserNotFound | DbError>
}

class PostgresUserRepo implements UserRepo {
  findById = (id) => Effect.tryPromise({
    try: () => pg.query("SELECT * FROM users WHERE id = $1", [id]),
    catch: (e) => toDbError(e)
  })
}
```

Business code depends on `UserRepo`, not `pg`. Tests use in-memory `UserRepo`.

## Module Boundaries

- One concern per module. Name after the concept, not the file type.
- Public API: explicit exports. Internal: not exported or in `internal/`.
- No circular deps. If A imports B, B does not import A.
- Index files are minimal — only the public surface.

## Common Mistakes

`any`; `throw` for domain; raw errors in `Promise<T>`; `console.log` / `Date.now` in business logic; `JSON.parse` deep in stack; tests that mock what they test; types that mirror DB schema; stringly-typed enums; global state; `as` casts.

## Red Flags

`any` in production; untyped `JSON.parse`; `try/catch` around `await`; `Date.now()` in logic; `console.log` left; `data: any`; circular imports; tests that don't test.

## Anti-Patterns

**"Just a string"** (no branded type); **"errors are exceptions"**; **"types later"**; **"test with mock"** (test seam); **"any to unblock"**; **"utils.ts"**.

## Verification

- Scan for red flags: no `any` in production, no untyped `JSON.parse`, no `try/catch` around `await`, no `Date.now()` in logic, no leftover `console.log`, no `data: any`, no circular imports.
- Tests exercise behavior through test seams — in-memory implementations of the domain interfaces — not mocks of what they test (Adapters, Common Mistakes).

## Skill Result Contract

```
<skill_result>
  <skill><name></skill>
  <status>success|partial|blocked|failure</status>
  <evidence>…</evidence>
  <artifacts>…</artifacts>
  <risks>…</risks>
</skill_result>
```

## References

N/A — no references/ directory; the skill is a self-contained prompt corpus.
