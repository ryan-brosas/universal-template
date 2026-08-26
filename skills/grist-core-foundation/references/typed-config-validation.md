<!-- capsule-v2 -->
# Typed config API validation — how do you expose arbitrary install/org config keys over REST without a validation gap?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Config keys are an open-ended registry — how do middleware-level validators keep PUT bodies key-and-value correct before any handler runs?

## Checker-registry middleware: ConfigKeyChecker on params, then ConfigValueCheckers[key].check(body) → 400 with userError detail
**Path/Symbol:** `app/server/lib/attachEarlyEndpoints.ts`: `hasValidConfig` / `hasValidConfigKey` middlewares (418–434), `assertValidConfig` (436–449), `assertValidConfigKey` (451–462); checker sources `ConfigKeyChecker`, `ConfigValueCheckers` from `app/common/Config`; audit trail `logCreateOrUpdateConfigEvents` previous+current (328–360).
**Signature:** `(req, res, next)` express middlewares; `ConfigValueCheckers[key].check(req.body)` throws ts-interface-checker errors.
**Data Shape:** valid keys are a closed enum; values vary per key; error payload `{ userError: String(err) }`.

### Decisive source
```ts
function assertValidConfig(req: Request) {
  assertValidConfigKey(req);
  const key = stringParam(req.params.key, "key") as ConfigKey;
  try {
    ConfigValueCheckers[key].check(req.body);
  } catch (err) {
    log.warn(`Error during API call to ${req.path}: invalid config value (${String(err)})`);
    throw new ApiError("Invalid config value", 400, { userError: String(err) });
  }
}
// update result may be PreviousAndCurrent<Config> — "previous" in data distinguishes
// an UPDATE audit event from a CREATE one.
```

**Flow:** route chain = json body parser (`strict:false`) → hasValidConfig(Key) → handler; the KEY check runs first so unknown keys fail with a distinct message; VALUE check dispatches through a registry keyed by the same enum, so adding a config key means adding its checker once and every route inherits validation. Handlers then branch audit events on `"previous" in result.data` to emit create-vs-update with full before/after snapshots.
**Invariant:** validation lives OUTSIDE handlers so no code path can persist unvalidated config; the client-facing error carries the checker's message via userError while the generic ApiError message stays stable; GET/PUT/DELETE share identical key middleware (PUT adds value check).
**Probe:** exercised via admin/config API suites in `test/gen-server/*ApiServer*`; direct unit test of the two middlewares absent at this pin — caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "ConfigValueCheckers ConfigKeyChecker assertValidConfig getInstallConfig", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the registry-dispatch validator whenever configuration is schema-per-key: it keeps REST validation declarative and colocated with the type definitions. Adapt to zod/io-ts equivalents. Omit the previous/current audit split if you have no audit requirement — but keep the key-before-value ordering.
