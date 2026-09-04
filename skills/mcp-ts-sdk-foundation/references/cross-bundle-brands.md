<!-- capsule-v2 -->
# Cross-bundle error branding — how does `instanceof` keep working when two copies of your SDK are loaded in one process?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** Client and server each bundle their own core copy, so prototype-identity instanceof fails for dual-role processes — what replaces it?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/errors/crossBundleBrand.ts`: `stampErrorBrands` (:60-72), `brandedHasInstance` (Symbol.hasInstance override), registry `BRANDS = Symbol.for('mcp.sdk.errorBrands')` (:54); brand consumers in `errors/sdkErrors.ts` (`SdkError`, `SdkHttpError`, …) and per-package error classes.
**Signature:** `stampErrorBrands(instance: object, ctor: unknown): void` — called ONCE from the hierarchy root's constructor with `new.target`; subclasses inherit stamping without touching constructors.
**Data Shape:** Every class chain that declares an OWN static `mcpBrand` contributes its string to a Set stored under the registry symbol on the instance; `instanceof` resolves via `Symbol.hasInstance` against the brand set, with ordinary prototype check as fallback.

### Decisive source
```ts
// Brands assert identity, not shape: brand strings are version-less, so an
// instance from one SDK version matches the class of another. Members added
// to a branded class in a later version may be absent on a matched instance —
// read fields defensively … Constructor-time only: never stamp arbitrary
// objects. A stamped non-instance would satisfy instanceof while lacking the
// prototype members callers reach for after the check.
```

**Flow:** construct → root ctor stamps brands of every chain class with an own `mcpBrand` (own-property test excludes inherited) → later `x instanceof Cls` hits `Symbol.hasInstance` → brand-set membership decides → unbranded objects fall back to plain prototype semantics. The escape hatch for breaking changes: rename the brand string in the same release, severing cross-version matching deliberately; brand pins tests make renames loud.

**Invariant:** Participation criterion — EVERY exported error class callers are told to `instanceof` must be branded (per-package conformance tests walk export surfaces and fail naming any opt-out). User-defined subclasses WITHOUT their own brand keep plain prototype semantics, so a foreign base-class instance never satisfies `instanceof UserSubclass`. Property mangling (`mangle.props`) would break brand statics; default esbuild/webpack/terser settings do not. Same prior art as Node stream.Writable / undici / AWS SDK ServiceException.

**Probe:** `packages/core-internal/test/errors/crossBundleBrand.test.ts` :56 ("an instance from a second module copy satisfies instanceof against this copy"), :95 ("isInstance guards agree with instanceof … across module copies"); surface pins via each package's `errorBrandConformance.test.ts`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "stampErrorBrands brandedHasInstance mcpBrand", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt brand-stamp + Symbol.hasInstance for any multi-entry library whose classes cross bundle boundaries; adapt brand strings/namespacing; omit the conformance-test machinery only if you have another enforcement net.
