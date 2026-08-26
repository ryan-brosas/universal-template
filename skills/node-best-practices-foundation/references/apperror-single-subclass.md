<!-- capsule-v2 -->
# AppError single-subclass rule — why extend Error exactly once, and what does a porter get wrong about the prototype chain?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** How should an application error class be shaped so errors stay uniform, keep stack traces, and differentiate cases without a class explosion?

## One subclass, data-differentiated
**Path/Symbol:** `sections/errorhandling/useonlythebuiltinerror.md` (JS factory :44-53, TS class :57-70) + `sections/errorhandling/shuttingtheprocess.md` (:50-60 TS variant).
**Signature:** TS: `class AppError extends Error { constructor(name, httpCode, description, isOperational) }`; JS: `function AppError(name, httpCode, description, isOperational)` with `AppError.prototype = Object.create(Error.prototype); AppError.prototype.constructor = AppError;`.
**Data Shape:** fields `name`, `httpCode`, `description`, `isOperational`. Throw sites pass an enum-ish constant pair (`commonErrors.resourceNotFound`, `commonHTTPErrors.notFound`) — kinds are DATA, not classes. Anti-patterns called out: `throw 'string'` (loses stack + breaks `instanceof` contracts across modules), and per-case subclasses (DbError/HttpError…) which "don't add too much value" (Ben Nadel / machadogj quotes).

### Decisive source
```typescript
// useonlythebuiltinerror.md :58-67
export class AppError extends Error {
  public readonly name: string;
  public readonly httpCode: HttpCode;
  public readonly isOperational: boolean;
  constructor(name: string, httpCode: HttpCode, description: string, isOperational: boolean) {
    super(description);
    Object.setPrototypeOf(this, new.target.prototype); // restore prototype chain
    this.name = name; this.httpCode = httpCode; this.isOperational = isOperational;
    Error.captureStackTrace(this);
  }
}
```

**Flow:** throw site constructs one AppError with kind-constants → any handler can branch on `.name`/`.httpCode`/`.isOperational` via property checks → uniform structure survives module boundaries and `instanceof Error` checks in third-party code.
**Invariant:** extending Error in ES2015+ WITHOUT `Object.setPrototypeOf(this, new.target.prototype)` yields instances whose prototype chain is broken — subsequent property assignments land on the wrong object and `instanceof AppError` fails. This line is load-bearing, not cosmetic. Extend once; never once-per-error-kind.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'setPrototypeOf(this, new.target.prototype)' sections/errorhandling/useonlythebuiltinerror.md sections/errorhandling/shuttingtheprocess.md` ≥ 1 each.

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "captureStackTrace", "limit": 10}'
# resolves `sections/errorhandling/shuttingtheprocess.md`, `sections/errorhandling/useonlythebuiltinerror.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the single-AppError + property-differentiation shape for any OO error port; adopt the JS-factory twin for pre-class codebases. Adapt field names per host domain. Omit string/custom-type throwing outright — documented anti-pattern.
