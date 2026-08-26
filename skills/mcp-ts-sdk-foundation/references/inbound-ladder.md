<!-- capsule-v2 -->
# Inbound validation ladder — what rejects a dual-era HTTP request, in what order, with which HTTP status?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How does one HTTP entry serve two protocol eras on one endpoint without ever silently downgrading a request to legacy?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/shared/inboundClassification.ts`: `classifyInboundRequest` (:878-920), `classifyRequestBody` (:702+), `classifyBatch` (:656-700), `INBOUND_VALIDATION_LADDER` (:261-374, ladder-as-data), `LADDER_ERROR_HTTP_STATUS` (:396-403), `httpStatusForErrorCode` (:422-427), `modernOnlyStrictRejection` (:941-988), `HEADER_MISMATCH_ERROR_CODE = -32020` (:223); NEW at this pin: `version-header-missing` presence cell (:539-557) — see version-header-presence-gate.md.
**Signature:** `classifyInboundRequest(request: InboundHttpRequest): InboundClassificationOutcome` where outcome = `InboundLegacyRoute {kind:'legacy', reason}` | `InboundModernRoute {kind:'modern', messageKind, message, classification}` | `InboundLadderRejection {kind:'reject', rung, cell, httpStatus, code, message, settled}`.
**Data Shape:** Legacy routes deliberately carry NO MessageClassification — hand-wired 2025 dispatch stays byte-identical. Rejections carry a stable `cell` id (test sheet key), the JSON-RPC error, and the HTTP status.

### Decisive source
```ts
// Body-primary era classification … `initialize` is legacy BY DEFINITION —
// unless it carries a valid envelope claim naming a modern revision, in which
// case the claim wins and the modern registry answers it method-not-found.
if (method === 'initialize' && !carriesValidModernEnvelopeClaim(params)) {   // :715
    if (headerNamesModern) return crossCheckMismatch('initialize-with-modern-header', headerVersion,
        'an initialize request (legacy handshake) was sent with a modern MCP-Protocol-Version header');
    return { kind: 'legacy', reason: 'initialize', ...(requestedVersion !== undefined && { requestedVersion }) };
}
```
Ladder order: 1 http-method (non-POST → legacy route; 405 on modern-only) → 2 jsonrpc-shape (batches element-wise: ANY modern/invalid element ⇒ whole array rejected) → 3 era-classification (−32020 header/body mismatch, −32602 missing envelope behind a modern header claim) → 4 envelope (−32602 naming offending keys — the ONLY invalid-params that maps to HTTP 400 at the edge) → 5 method-registry / 6 request-params (dispatch, in-band on 200) → 7 standard-header / 8 client-capabilities / 9 param-header (pre-dispatch; documented order is NOT observed precedence — see invariant; rung 7 now OPENS with the version-header-missing presence cell on request POSTs).

**Flow:** strip RFC 9110 OWS from headers → non-POST ⇒ legacy route → array ⇒ classifyBatch → posted response ⇒ legacy session traffic → request/notification ⇒ body-primary classification with header as cross-check ONLY (never upgrades/downgrades). Malformed claims are loud rejections, never silent legacy fallback.

**Invariant:** A header/body disagreement is an explicit ladder outcome (−32020/400), never a resolution. Handler-produced errors stay in-band on HTTP 200 whatever their code — EXCEPT −32021 (MissingRequiredClientCapability), whose 400 the spec mandates per-error. The per-request transport indexes LADDER_ERROR_HTTP_STATUS directly because `httpStatusForErrorCode`'s `?? 400` fallback would wrongly map dispatch-window codes outside the table. Pre-dispatch rungs 7–9 run BEFORE dispatch rungs 5–6 observably, so a request failing both is answered by the later-numbered rung first — the rationale strings encode this trap explicitly.

**Probe:** `packages/core-internal/test/shared/inboundClassification.test.ts` (52 tests); cell-sheet pinning via `packages/core-internal/test/shared/inboundLadderCellSheet.test.ts`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "classifyInboundRequest INBOUND_VALIDATION_LADDER httpStatusForErrorCode", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt body-primary classification + ladder-as-data + origin-keyed HTTP status mapping; adapt rung set to your spec surface; omit conformance-cell ids unless you mirror the published suite.
