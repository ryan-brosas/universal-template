<!-- capsule-v2 -->
# Types and nullability — are unknowns narrowed and aliases honest?

**Source:** Google tsguide §Type system; TS handbook Do's/Don'ts. **Question:** Does the type layer express absence and callbacks without `any` or smuggled null unions?

## Unknown and any seam
**Path/Symbol:** function parameters, catch bindings, external JSON.
**Signature:** `unknown` at boundary; narrow before use; no production `any`.
**Data Shape:** `const val: unknown = input; if (isUser(val)) { ... }`

### Decisive contrast
```typescript
// Wrong — disables checking
function parse(raw: any): User { return raw; }

// Right — narrow at edge
function parse(raw: unknown): User {
  return UserSchema.parse(raw);
}

// Wrong — boxed primitive
function reverse(s: String): String { return s.split('').reverse().join(''); }

// Right
function reverse(s: string): string { return [...s].reverse().join(''); }
```

**Flow:** accept `unknown` → validate/narrow → operate on concrete type inside module.
**Invariant:** finished TS code has **no `any`** except documented migration islands.
**Probe:** eslint `@typescript-eslint/no-explicit-any`; grep `\bany\b` in non-test `.ts` files.

## Nullability and aliases seam
```typescript
// Wrong — nullable alias spreads null everywhere
type CoffeeResponse = Latte | Americano | undefined;
function getLatte(): CoffeeResponse { ... }

// Right — nullability at use site
type CoffeeResponse = Latte | Americano;
function getLatte(): CoffeeResponse | undefined { ... }

// OK — explicit nullish check (Google)
if (foo == null) { /* null or undefined */ }

// Prefer optional over |undefined in params
function connect(host: string, port?: number) {}
```

**Flow:** define non-null aliases → add `|null` / `|undefined` only where consumed → optional params for omitted args.
**Invariant:** exported type aliases do **not** embed `|null` or `|undefined`.
**Probe:** review exported `type` declarations; optional params used instead of duplicate overloads.

## Callback and overload seam
```typescript
// Wrong — any return silences mistakes
function onClick(fn: () => any) { fn(); }

// Right
function onClick(fn: () => void) { fn(); }

// Wrong — optional callback param implies two call shapes
interface Fetcher {
  getObject(done: (data: unknown, elapsedTime?: number) => void): void;
}

// Right — non-optional; caller may ignore second arg
interface Fetcher {
  getObject(done: (data: unknown, elapsedTime: number) => void): void;
}

// Overloads: specific before general; prefer unions/optionals
declare function fn(x: HTMLDivElement): string;
declare function fn(x: HTMLElement): number;
declare function fn(x: unknown): unknown;
```

**Flow:** callbacks use `void` when return ignored → avoid optional callback parameters → collapse trailing overloads to optionals/unions.
**Invariant:** overload order is **most specific first**; no unused generic type parameters.
**Probe:** handbook overload examples pass; `@typescript-eslint/unified-signatures` where configured.

## Verdict
TypeScript style treats types as contracts: `unknown` at edges, no nullable aliases, honest callbacks. Domain modeling rules live in `typescript-coding-standards`. Learning note: `typescript-style-learning-note.md`.
