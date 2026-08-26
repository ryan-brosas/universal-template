<!-- capsule-v2 -->
# NcError versioned taxonomy — how does one static facade serve v1's 403s and v3's 422s from the same call site?

**Source:** NocoDB Sustainable Use License `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory project `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** When the same service method must return different status codes and error shapes per API version, where does the version switch live — and what does each version change?

## Context-selected singleton pair (NcErrorV1 default / NcErrorV3 override) + backward-compat statics

**Path/Symbol:** `packages/nocodb/src/helpers/ncError.ts:NcError.get` (:20–25) + ~90 delegating statics (:28–399); `packages/nocodb/src/helpers/NcErrorV1.ts:NcErrorV1` (:38–143) with `AjvError` (:13–26) and `NcZodError` (:28–37); `packages/nocodb/src/helpers/ncErrorV3.ts:NcErrorV3` (:22–105) with `AjvErrorV3` (:5–20).
**Signature:** `static get(context?: { api_version?: NcApiVersion }): NcErrorV1 | NcErrorV3` — V3 only when `context.api_version === NcApiVersion.V3`, else V1; every static mirrors `NcError._.<method>(args)` so legacy callsites never break.
**Data Shape:** Errors ride `errorCodex.generateError(NcErrorType, {params/customMessage, details?})`; V1 not-founds are 403-shaped by SDK defaults while V3 RE-REGISTERS fourteen codex entries to 422 (`Invalid filter expression: …`, `Base '<id>' not found`, `Table …`, `View …`, `Field …`, `Filter …`, `Team …`, `User …`, `Extension …`, `Dashboard …`, `Widget …`, `Workflow …`, `Script …`, `RLS Policy …`).

### Decisive source
```ts
// ncError.ts :19-25 — the entire version dispatch
// return ncError based on api version
static get(context?: { api_version?: NcApiVersion }) {
  if (context?.api_version === NcApiVersion.V3) {
    return NcError._V3;
  }
  return NcError._;
}
```

**Flow:** services call `NcError.get(context).tableNotFound(id)` — the context threaded through every request carries `api_version`; V3 extends V1 (constructor chains super() then overrides codexes) so un-overridden methods keep V1 semantics. Divergence points beyond the codex table: `invalidRequestBody` — V1 delegates to `badRequest` ("backward compatibility for v1 and v2 apis", :125–128) vs V3 throws ERR_INVALID_REQUEST_BODY properly; `ajvValidationError` — V1 throws legacy `AjvError extends NcBaseError` vs V3 throws `AjvErrorV3 extends NcBaseErrorv2` carrying details; `recordNotFound` formats composite ids by joining multi-key values with `'___'` and escaping underscores (`replaceAll('_', '\\_')`) or falls back to single-value/'unknown' (:66–111); V1 constructor overrides exactly one codex (ERR_INVALID_LIMIT_VALUE message built from `defaultLimitConfig` bounds, code 422).
**Invariant:** (1) The version gate is a SINGLE ternary on context — adding a second switch site forks behavior silently; porters must route ALL error emission through `.get(context)`. (2) Static methods are compatibility shims pinned to V1 (`return NcError._.…`): calling a static BYPASSES version selection by design, which is why new code must use the instance path. (3) NcZodError is version-agnostic (always NcBaseErrorv2/400/ERR_INVALID_REQUEST_BODY).

### Porting traps (each verified against source)
- V3's fourteen-codex table is DATA, not code — the whole behavioral diff of v3 errors is one `setErrorCodexes({...})` map plus two method overrides; port it as a table.
- In-file anchors: `grep -c "api_version === NcApiVersion.V3" src/helpers/ncError.ts` → 1; `grep -c "replaceAll('_'" src/helpers/NcErrorV1.ts` → 2; `grep -n 'ERR_RLS_POLICY_NOT_FOUND' src/helpers/ncErrorV3.ts` → :78 region.

**Probe:** Deterministic probe from repo root:
`cd packages/nocodb && grep -n 'static get(context' src/helpers/ncError.ts | cut -d: -f1` → `20` and `sed -n '30,82p' src/helpers/ncErrorV3.ts | grep -c 'code: 422'` → `13`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "NcErrorV1 NcErrorV3 errorCodex recordNotFound", limit: 10 });
```
Resolves `NcErrorV1.recordNotFound` :66-111 rank-1, `NcErrorV3.constructor` :23-83 rank-2.

## Verdict
Adopt the context-selected singleton pair, the data-table versioning of status codes, and the static-shim doctrine; adapt NcErrorType enum and message grammar to host; omit Ajv/Zod specifics if host validation differs. Coverage caveat: no direct tests at pin; probes are source-greps.
