<!-- capsule-v2 -->
# Token-symbol DI layer — how do you wire ports-and-adapters so the core package has ZERO runtime dependencies on adapters?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What does the dependency-injection surface look like that lets hexagonal architecture hold at runtime (core compiled with no adapter imports)?

## tsyringe re-export + Symbol tokens + Noop default implementations
**Path/Symbol:** `packages/v2/di/src/index.ts` (whole file, 38L): curated tsyringe re-exports (`container`, `inject`, `injectable`, `injectAll`, `scoped`, `singleton`, `registry`, `Lifecycle`, `injectWithTransform`…), token factory `createToken<T>(description): InjectionToken<T> => Symbol(description)` (:29–31), child-container factory `createChildContainer()` (:34–36); core token registry `packages/v2/core/src/ports/tokens.ts:v2CoreTokens`; per-adapter token files e.g. `adapter-table-repository-postgres/src/record/di/tokens.ts:v2RecordRepositoryPostgresTokens`; Noop defaults `packages/v2/core/src/ports/defaults/*` (`NoopUnitOfWork`, `NoopEventBus`, `NoopTracer`, `NoopLogger`, `NoopRecordOrderCalculator`, `NoopUndoRedoStore`, …).
**Signature:** `createToken<T>(description: string): InjectionToken<T>` — one line; every binding elsewhere uses `@inject(v2CoreTokens.somePort)` with `@injectable()` classes.
**Data Shape:** each package owns a `<pkg>Tokens` object whose values are UNIQUE SYMBOLS (`tokens.spec.ts` asserts all values are symbols and pairwise unique); interfaces live in core `ports/`, implementations register against symbols in adapter packages or the composition root.

### Decisive source
```ts
export const createToken = <T>(description: string): InjectionToken<T> =>
  Symbol(description) as InjectionToken<T>;

export const createChildContainer = (): DependencyContainer =>
  container.createChildContainer();
// tokens.spec.ts invariant:
//   values.every((value) => typeof value === 'symbol') === true
//   new Set(values).size === values.length
```

**Flow:** core defines port INTERFACE + Symbol token (+ often a Noop implementation usable in tests/tools) → adapter packages implement the interface, annotate `@injectable()`, resolve collaborators by symbol → the host composition root registers concrete bindings into a (child) container per app instance → request-scoped behavior comes from child containers rather than mutating globals. Because `@teable/v2-core` depends only on `@teable/v2-di` (which re-exports tsyringe), the hexagonal boundary is enforced by the import graph itself.
**Invariant:** core NEVER imports an adapter package — only `reflect-metadata` + tsyringe cross that boundary; tokens are symbols so string collisions across packages are impossible; the export list is CURATED (no wildcard `export *` of tsyringe) keeping the DI API surface reviewable.
**Probe:** `packages/v2/core/src/index.spec.ts::"re-exports key domain and port modules"` (:5–14 — asserts Table/MemoryCommandBus/NoopEventBus/v2CoreTokens are exported); `packages/v2/core/src/ports/tokens.spec.ts::"defines unique symbols"` (:4–11).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable",
  query: "createToken v2CoreTokens injectable", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the symbol-token registry + curated DI re-export module + Noop-defaults trio as the skeleton of any ports-and-adapters codebase. Adapt the underlying container (tsyringe vs your own registry/Nest providers) — the CONTRACT is "core has no adapter deps; tokens are unique symbols." Omit decorator-based injection if your host forbids decorators (pass factories instead).
