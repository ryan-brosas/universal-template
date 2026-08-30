<!-- capsule-v2 -->
# Elicitation leg split — why does the legacy shim need a capability-check-free, accept-unvalidated elicitation core?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** One `elicitInput` API serves public callers and the internal shim — how do their differing gate and validation rules coexist without duplicating the request path?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/server.ts`: `elicitInput` (:1159-1179), `_sendElicitationLeg` (:1189-1234), shim wiring passing `{validateAcceptedContent: false}` (:300), form-mode default + per-mode capability checks.
**Signature:** `_sendElicitationLeg(params, options?, behavior?: {validateAcceptedContent: boolean}): Promise<ElicitResult>`.
**Data Shape:** mode `'form'|'url'` (form default when omitted); url ⇒ requires `elicitation.url`; form ⇒ requires `elicitation.form`.

### Decisive source
```ts
// The capability-check-free core of elicitInput. The shim uses it because its gate differs
// from the public checks: a bare `elicitation: {}` counts as form support (the pre-mode rule),
// and accepted content passes through UNVALIDATED for parity with the modern client driver
// (handlers validate via the schema-aware acceptedContent overload and can re-ask).
private async _sendElicitationLeg(params, options?, behavior?) {
    ...
    case 'form': {
        const result = await this.request({ method: 'elicitation/create', params: formParams }, options);
        if (validateAcceptedContent && result.action === 'accept' && result.content && formParams.requestedSchema) {
            const validationResult = validator(result.content);
            if (!validationResult.valid) throw new ProtocolError(InvalidParams,
                `Elicitation response content does not match requested schema: ...`);
        }
        return result;
    }
```

**Flow:** public path: guard → per-mode capability assert → leg with validation ON. Shim path: its own pre-mode gate (`elicitation:{}` = form-capable) → leg with validation OFF → accepted content flows to the handler unvalidated. Validator errors are ProtocolErrors; validator CRASHES are rewrapped InternalError (`Error validating elicitation response`) — only genuine InvalidParams propagate untouched.

**Invariant:** Two gates exist by DESIGN — collapsing them either blocks legitimate shim traffic (strict url check vs bare-elicitation form rule) or weakens public callers. Validation-off is parity with the modern client driver, NOT a hole: handlers own validation through the schema-aware acceptedContent overload and may re-ask.

**Probe:** `packages/server/test/server/legacyInputRequiredShim.test.ts` (shim legs through `_sendElicitationLeg`, :1-789 suite incl. harness `legacyShimHarness.ts`); integration elicitation legs in `test/e2e/scenarios/flow.test.ts`; coverage caveat: no dedicated unit file for `_sendElicitationLeg` at this pin — pinned via shim suite + e2e.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "_sendElicitationLeg elicitInput validateAcceptedContent LegacyInputRequiredShim", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt internal-leg-with-different-gate composition over flag-tangled public methods; adapt mode/capability vocabulary; omit URL-elicitation protocol details (SEP-era docs).
