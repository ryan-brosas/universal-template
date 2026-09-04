<!-- capsule-v2 -->
|# Attachment upload error triage — typed first-error rethrow vs generic 500 mask

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** When a multi-file upload partially fails, how does the service decide between surfacing the real error and masking it?

## Path/Symbol
`packages/nocodb/src/services/attachments.service.ts` upload error block (~200–209); producer gate sibling block :211–225.

**Signature:** collect per-attachment `errors: {error}[]` → log ALL → inspect `errors[0].error` type → rethrow or wrap.

**Data Shape:** uploads are attempted per attachment with failures COLLECTED, not fail-fast; the thrown shape is decided by instanceof on the first error only.

### Decisive source
```ts
errors.forEach((error) => this.logger.error(error));       // full evidence always logged

const firstError = errors[0].error;
if (firstError instanceof NcError || firstError instanceof NcBaseError) {
  throw firstError;                                        // typed → preserve semantics/status
}
NcError.internalServerError('Failed to upload attachment'); // untyped → generic 500 mask
```

**Flow:** attempt all attachments → every failure logged individually → first error decides the thrown shape: framework-typed errors keep identity (clients see real status/message); foreign errors collapse into one internal-server-error so internals never leak.

**Invariant:** (1) Log-everything / throw-one: response shape is decided by ERROR TYPE, not count. (2) The instanceof whitelist is the security boundary — only known-safe classes reach clients verbatim. (3) First-error-wins keeps responses deterministic for identical input. (4) Pairs with the thumbnail gate that follows: failed uploads don't enqueue thumbnails, successes do — one pass, two decisions.

**Probe:** no unit test upstream. Source-grounded probe: attachments.service.ts:200-225 verbatim; pairing capsule import-error-ladder.md (batch-failure philosophy at scale).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "NcBaseError internalServerError attachmentsService upload", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt typed-first-error rethrow with generic fallback masking; adapt error class names; omit nothing. Coverage caveat: no in-repo unit tests; source-grounded.
