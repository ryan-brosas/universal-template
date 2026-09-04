<!-- capsule-v2 -->
# `vi.spyOn` descriptor ownership — how does spying survive prototype methods, getters, Vite-SSR getters, and ESM namespaces, and what exactly does restore undo?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@c3ba16b35847`); Codebase Memory `vitest`. **Question:** When you spy on a method that lives on a prototype (or behind a getter), what gets written where, and how can restore possibly put it back correctly?

## `spyOn` + `getDescriptor` in packages/spy
**Path/Symbol:** `packages/spy/src/index.ts:spyOn` (320–446), `getDescriptor` (448–461), closure `reassign`/`restore` (388–412); implementation-selection ladder in `createMock` (486–519).
**Signature:** `spyOn<T, K>(object: T, key: K, accessor?: 'get'|'set'): Mock<Procedure|Constructable>`; `getDescriptor(obj, method): [ownerObject, PropertyDescriptor] | undefined`.
**Data Shape:** walks the prototype chain returning the OWNER plus its descriptor; mock replaces only the accessor named by `accessType` ('value'|'get'|'set'); idempotent — spying an existing Mock returns it unchanged.

### Decisive source
```ts
const [originalDescriptorObject, originalDescriptor] = getDescriptor(object, key) || []
assert(originalDescriptor || key in object,
  `The property "${String(key)}" is not defined on the ${typeof object}.`)
let accessType: 'get' | 'set' | 'value' = accessor || 'value'
let ssr = false
// vite ssr support - actual function is stored inside a getter
if (accessType === 'value' && originalDescriptor
    && originalDescriptor.value == null && originalDescriptor.get) {
  accessType = 'get'; ssr = true                          // unwrap through the getter
}
...
const reassign = (cb: any) => {
  const { value, ...desc } = originalDescriptor || { configurable: true, writable: true }
  if (accessType !== 'value') delete desc.writable        // accessors can't be writable
  ;(desc as PropertyDescriptor)[accessType] = cb
  Object.defineProperty(object, key, desc)                // ALWAYS defines on the receiver
}
const restore = () => {
  // if method is defined on the prototype, we can just remove it from
  // the current object instead of redefining a copy of it
  if (originalDescriptorObject !== object) Reflect.deleteProperty(object, key)
  else if (originalDescriptor && !original) Object.defineProperty(object, key, originalDescriptor)
  else reassign(original)
}
```
Implementation ladder per call:
```ts
config.onceMockImplementations.shift() || config.mockImplementation
  || prototypeConfig?.onceMockImplementations.shift() || prototypeConfig?.mockImplementation
  || original || noopImplementation
```

**Flow:** `getDescriptor` finds owner+descriptor up the proto chain → SSR detection (null value + get ⇒ real fn hides behind a Vite-SSR getter; spy reads through it once with `original()` and reassigns a `() => mock` GETTER) → assert spy-ability (function, or accessor on a static value) → idempotence short-circuit (`isMockFunction(original)` returns it) → `reassign(mock)` writes an OWN property onto the receiver preserving every descriptor attribute except swapping the accessor → at restore time the OWNER decides the strategy. Proxy/ESM guards: a TypeError mentioning "Cannot redefine property"/"Cannot replace module namespace" on a `Module`-tagged object is rethrown as an actionable message pointing to vi.mock docs.
**Invariant:** (1) spying always creates an own property on the RECEIVER, never mutates the prototype — sibling instances are untouched; (2) restoring an inherited method DELETES the own property (restores natural lookup) instead of copying the original down, which would freeze a snapshot of the prototype; (3) restore of a newly-created property redefines the saved originalDescriptor verbatim; (4) the implementation ladder means once-implementations queue-consume before base implementations, falling back to `original`, then noop; (5) automocked class methods are exempt from both `mockRestore` and `restoreAllMocks` original-restoration (they reset history only) — pinned by dedicated tests.
**Probe:** `test/unit/test/spy.test.ts` (happy-dom env; spies `localStorage.getItem`, class constructor via `mockImplementationOnce`, instance method); `test/unit/test/mocked-class-restore-all.test.ts` + `mocked-class-restore-explicit.test.ts` pin the automock/restore boundary behavior inline-snapshot style. Caveat: unit suite needs installed deps; source read byte-for-byte at pinned HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", file_pattern: "packages/spy/src/index.ts", label: "Function", limit: 25 });
// observed 44 functions incl. spyOn-family overloads, getDescriptor 448-461,
// reassign/restore 388-412, createMock 471-625, reparentMockPrototype 630-645,
// restoreAllMocks/clearAllMocks/resetAllMocks 752-765.
```

## Verdict
Adopt owner-aware restore (delete vs redefine vs reassign) and receiver-only writes for any monkey-patching layer — this is what makes spies composable across instances. Adapt the SSR-getter unwrap to your bundler's output shape and keep the actionable ESM-namespace error. Omit constructor/class mocking extras unless your host mocks classes.
