<!-- capsule-v2 -->
# Version-header presence gate — why a modern POST without MCP-Protocol-Version is refused one rung later, and by which cell?

**Source:** typescript-sdk MIT `main@3924de9` (commit 75dc7ea6 #2590); Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How does an HTTP entry enforce the SEP-2243 required standard headers without breaking body-primary era classification?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/shared/inboundClassification.ts`: `validateStandardRequestHeaders` (:536-616) — new FIRST cell `version-header-missing` (:539-557); ladder rationale updated in `INBOUND_VALIDATION_LADDER` (:261-374, standard-header-validation rung :326-352); `packages/server/src/server/createMcpHandler.ts`: shared reader `standardHeadersOf` (:421-427) feeding BOTH the classifier (:490) and the presence gate (:695).
**Signature:** `validateStandardRequestHeaders(request: InboundHttpRequest, route: InboundModernRoute): InboundLadderRejection | undefined`; `standardHeadersOf(request: Request): Omit<InboundHttpRequest, 'httpMethod' | 'body'>`.
**Data Shape:** Rejection carries stable cell id `version-header-missing`, code -32020 (HEADER_MISMATCH_ERROR_CODE :223), HTTP 400; message names the body envelope's claimed revision when present ("the body envelope names protocol version X but the required MCP-Protocol-Version header is absent").

### Decisive source
```ts
// inboundClassification.ts :536-557 (inside validateStandardRequestHeaders,
// AFTER the messageKind !== 'request' early return)
// The presence check lives here rather than in `classifyInboundRequest`
// on purpose: classification stays body-primary (a proxy stripping the
// header must not change the era), and only this rung refuses to serve
// the request.
if (request.protocolVersionHeader === undefined) {
    const claimed = route.classification.revision;
    return crossCheckMismatch(
        'version-header-missing',
        '(missing)',
        claimed === undefined
            ? 'the body carries a modern per-request envelope but the required MCP-Protocol-Version header is absent'
            : `the body envelope names protocol version ${claimed} but the required MCP-Protocol-Version header is absent`,
        'standard-header-validation'
    );
}
```

**Flow:** request arrives → `classifyEntryRequest` reads headers ONCE via `standardHeadersOf` and classifies body-primary (absent header NEVER changes the era) → modern route passes the supported-revision gate → entry calls `validateStandardRequestHeaders` with the SAME header snapshot → requests missing `MCP-Protocol-Version` are refused by the NEW first cell BEFORE `method-header-missing`/`name-header-missing` (SEP-2243 lists protocol-version first among required headers, so a request missing both is answered by it). Notification POSTs are exempt: the rung returns undefined for `messageKind !== 'request'`, so a modern-enveloped notification is dispatched even with no standard headers at all.

**Invariant:** Classification and enforcement are deliberately SEPARATE rungs — a proxy stripping the header must not change the era (body-primary holds), yet the server still refuses to serve a headerless modern REQUEST. One shared header read (`standardHeadersOf`) feeds both halves; reading headers at one site but not the other is precisely the divergence that let this request be served before the fix. Observed precedence still puts this rung immediately after the supported-revision gate, ahead of dispatch rungs 5–6.

**Probe (direct tests):** `packages/core-internal/test/shared/standardHeaderValidation.test.ts` — :65 `a modern request without an MCP-Protocol-Version header is rejected (version-header-missing)`; second expectRejection at :87 (claimed-revision variant naming the body envelope's version). Entry layer `packages/server/test/server/stdHeaderValidation.test.ts`: :78 `a missing MCP-Protocol-Version header is rejected 400/-32020` (+ :93 message assertion `MCP-Protocol-Version header is absent`), :96 same rejection under the strict `legacy:'reject'` posture (spec's MAY-treat-as-2025 allowance only for servers still serving pre-2025-06-18 clients), :116 missing header never reaches the handler, :154 present-but-disagreeing header still rejected 400/-32020.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "validateStandardRequestHeaders crossCheckMismatch", limit: 3 });
// → validateStandardRequestHeaders Function …inboundClassification.ts 536-616; crossCheckMismatch 452-467
```

**Verdict:** Adopt single-read header plumbing + classify/enforce separation with request-only presence gates; adapt the cell ids if you mirror the published conformance sheet; omit the notification exemption only if your spec surface has no headerless-notification case.
