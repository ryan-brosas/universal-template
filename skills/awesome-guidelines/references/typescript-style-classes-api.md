<!-- capsule-v2 -->
# Classes and API surface — are TS classes lean and assertions rare?

**Source:** Google tsguide §Classes, §Enums, §Type assertions. **Question:** Do classes use TS visibility/readonly idioms without `#private`, `const enum`, or assertion spam?

## Class member seam
**Path/Symbol:** `class` declarations, fields, constructors.
**Signature:** `private` not `#`; `readonly` for immutable fields; parameter properties in ctor.
**Data Shape:** `constructor(private readonly repo: Repo) {}`

### Decisive contrast
```typescript
// Wrong — private identifiers (emit cost, ES2015 floor)
class Clazz {
  #ident = 1;
}

// Right
class Clazz {
  private ident = 1;
}

// Wrong — manual plumbing
class Foo {
  private readonly bar: Bar;
  constructor(bar: Bar) { this.bar = bar; }
}

// Right — parameter property
class Foo {
  constructor(private readonly bar: Bar) {}
}

// Wrong — const enum (invisible to consumers)
const enum Status { Active, Inactive }

// Right
enum Status { Active, Inactive }

// Wrong — enum in boolean context
if (level) { enableFeature(); }

// Right
if (level !== undefined && level !== SupportLevel.NONE) {
  enableFeature();
}
```

**Flow:** prefer file-scope functions/constants → class only for instance state → mark immutable fields `readonly` → omit redundant `public`.
**Invariant:** no `#private`, no `const enum`, no static `this`, no container classes with only static members.
**Probe:** grep `#\w+` in class bodies; no `const enum`; enum comparisons are explicit.

## Type assertion seam
```typescript
// Wrong — non-null assertion without proof
function process(el: HTMLElement | null) {
  el!.focus();
}

// Right — narrow first
function process(el: HTMLElement | null) {
  if (el == null) return;
  el.focus();
}

// Wrong — angle-bracket assertion
const foo = <Foo>bar;

// Right
const foo = bar as Foo;

// Prefer annotation on literals over assertion
const options: Options = { a: 1, b: 2 };
```

**Flow:** prefer control-flow narrowing → use `as` only when reasoning is local and obvious → double cast via `unknown` only when necessary.
**Invariant:** assertions do **not** replace validation at trust boundaries (use schemas — see `typescript-coding-standards`).
**Probe:** `@typescript-eslint/no-non-null-assertion` on changed files; catch clauses typed `unknown`.

## Arrays and readonly seam
```typescript
// Prefer shorthand array syntax
let names: string[];
let matrix: string[][];

// Readonly when exposing internal arrays
private readonly userList: string[] = [];
```

**Flow:** use `T[]` / `readonly T[]` over `Array<T>` unless project documents exception.
**Invariant:** multi-dimensional arrays use `T[][]` form for simple types.
**Probe:** consistent array syntax in public API types.

## Verdict
Keep classes thin; use TS features that compile predictably. Learning note: `typescript-style-learning-note.md`.
