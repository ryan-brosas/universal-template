<!-- capsule-v2 -->
# Realm-aware mock primitives — why does the mocker snapshot Object/Function/Error constructors, and when must it re-capture them from the vm context?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** How do mocks stay `instanceof`-correct and throw catchable errors when test code runs inside a different vm realm?

## Primitives capture + vm re-bind
**Path/Symbol:** `packages/vitest/src/runtime/moduleRunner/bareModuleMocker.ts:BareModuleMocker` (:24–60 — `primitives`, `createError`), `runtime/moduleRunner/moduleMocker.ts:VitestMocker.constructor` (:21–50), `mockObject` bridge (:210–248).
**Signature:** `primitives: { Object; Function; RegExp; Array; Map; Error; Symbol }`; `createError(message: string, codeFrame?: string): Error`.
**Data Shape:** captured once at construction from the worker's own globals; `Symbol: globalThis.Symbol` is explicit. When a `vm.Context` option exists, ALL SEVEN are replaced wholesale by evaluating `'({ Object, Error, Function, RegExp, Symbol, Array, Map })'` INSIDE that context.

### Decisive source
```ts
this.primitives = { Object, Error, Function, RegExp,
                    Symbol: globalThis.Symbol, Array, Map }
protected createError(message: string, codeFrame?: string): Error {
  const Error = this.primitives.Error      // host-realm constructor, not closure's
  const error = new Error(message)
  Object.assign(error, { codeFrame })
  return error
}
// moduleMocker.ts — wholesale replacement inside the test realm:
const context = this.options.context
if (context) {
  this.primitives = vm.runInContext(
    '({ Object, Error, Function, RegExp, Symbol, Array, Map })', context,
  )
}
```

**Flow:** mocker built in the harness realm → if tests execute in an injected vm context, primitives re-captured from that realm so `mockObject` walkers create arrays/maps/errors with the TEST realm's constructors → every mocker-raised error goes through `createError`, which instantiates with the CAPTURED `Error` and attaches `codeFrame` as an own property.
**Invariant:** never construct mock artifacts (spies' containers, automocked arrays/Maps, thrown errors) with the harness realm's constructors when the consumer realm differs — user code inside the vm gets `x instanceof Array === false` and `try/catch` misses the thrown error class. The re-capture must replace the whole tuple atomically (mixed realms break prototype checks both ways).
**Probe:** `test/e2e/test/mocking.test.ts` virtual-module + broken-factory cases assert mocker-thrown errors surface correctly (`errorTree()` snapshots :98/:125); `test/e2e/fixtures/no-module-runner/test/basic.test.ts` exercises `JSON`/`Math.sqrt()` mocking where builtin identity matters. Coverage caveat: no dedicated cross-realm unit test at this HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "BareModuleMocker primitives createError spyModule", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt capturing the seven constructors at mocker construction and routing all internal error creation through one factory. Adapt the re-capture trigger to your isolation boundary (vm context, worker realm, iframe). Omit the spyModule lazy-import branch (`spy.js` dist resolution) — host-specific plumbing.
