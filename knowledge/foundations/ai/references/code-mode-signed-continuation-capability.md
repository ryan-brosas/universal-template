<!-- capsule-v2 -->
# Code-mode signed continuation capability — how does an untrusted client hold a resumable sandbox without forging or replaying it?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** What makes the continuation token safe to hand to the model/client and persist across processes?

## HMAC over canonical JSON + time window
**Path/Symbol:** `packages/code-mode/src/continuation-capability.ts` — module defaults (:10–14), `setCodeModeContinuationSigningKey` (:21–31), `resolveCodeModeContinuationSecurity` (:33–56), `signCodeModeContinuation` (:58–79), `verifyCodeModeContinuation` (:81–128), `assertAuthShape` (:163–186), `constantTimeEqual` (:188–195), `canonicalJson` (:197–219).
**Signature:** auth = `{alg:'HMAC-SHA256', nonce:16-byte hex, issuedAtMs, expiresAtMs, signature}`; sig = `createHmac('sha256', key).update(canonicalJson(payload)).digest('base64url')`; default maxAge 60×60×1000 ms.
**Data Shape:** signing key hashed once to SHA-256 digest at runner construction (run-code-mode.ts:105–107) because the `run` codec wants fixed-length bytes; string and Uint8Array keys both accepted, empty string rejected.

### Decisive source
```ts
if (continuation.auth.expiresAtMs < now)
  throw new CodeModeProtocolError('Code mode continuation has expired.', ...);
if (continuation.auth.issuedAtMs > now + 60_000)   // future-issue tolerance
  throw new CodeModeProtocolError('Code mode continuation was issued in the future.', ...);
...
if (!constantTimeEqual(continuation.auth.signature, expected))
  throw new CodeModeProtocolError('Code mode continuation signature is invalid.');
```

**Flow:** verify = shape-lint the whole envelope (:85–102: version 2, non-empty token, ≥1 pending, resolutions array) → auth shape (alg pinned, nonce `^[0-9a-f]{32}$`, integer timestamps with expires>issued) → expiry window → HMAC comparison. Signature covers EVERYTHING except `auth.signature` itself (`stripSignature` :153–161), so js/toolNames/pendingInterruptions/resolutions are all tamper-proof — which is what makes the positional resume ledger trustable. `canonicalJson` sorts keys with `localeCompare` and DROPS undefined values recursively (:211–213), making signatures stable across JSON round-trips that reorder or omit undefined fields.
**Invariant:** if no key is configured, a fresh `randomBytes(32)` process default is used (:13) — continuations remain valid within one process but silently break across restarts unless the app pins a key (`experimental_setCodeModeContinuationSigningKey`). A porter who signs only the `token` field instead of the full envelope lets clients swap pendingInterruptions/resolutions. The 60s future-tolerance exists for clock skew between signer and verifier hosts; keep it or legit deployments fail.
**Probe:** deterministic (repo root): `grep -nF 'randomBytes(32)' packages/code-mode/src/continuation-capability.ts` → `13:` and `26:` (two sites); `grep -nF 'DEFAULT_MAX_AGE_MS = ' packages/code-mode/src/continuation-capability.ts` → `11:`; `grep -nF 'timingSafeEqual' packages/code-mode/src/continuation-capability.ts` → lines `1:`+`193:`; `grep -nF "localeCompare" packages/code-mode/src/continuation-capability.ts` → `213:`; `grep -nF 'now + 60_000' packages/code-mode/src/continuation-capability.ts` → `111:`; `grep -nF 'expiresAtMs < now' packages/code-mode/src/continuation-capability.ts` → `105:`. Direct tests: run-compatibility.test.ts:61–96 accepts legacy short key `'legacy-key'` end-to-end.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "signCodeModeContinuation verifyCodeModeContinuation canonicalJson", limit: 4 });` // verified live @9d9a73f: rank#1/#2 sign/verify :58-79/:81-128, rank#3 canonicalJson :197-219

## Verdict
Adopt full-envelope HMAC + canonical-JSON key sorting + constant-time compare as a unit; adapt key management (the random default is dev-only convenience); omit nothing — partial-envelope signatures defeat the entire capability design.
