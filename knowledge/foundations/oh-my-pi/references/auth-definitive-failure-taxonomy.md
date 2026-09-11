<!-- capsule-v2 -->
# Definitive-vs-transient OAuth failure handling — when is a failed credential soft-deleted, blocked, or retried?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT; Codebase Memory `oh-my-pi`. **Question:** What classifies a failure as "definitive", and what are the exact teardown vs backoff paths?

## Definitive-vs-transient OAuth failure handling
**Path/Symbol:** `packages/ai/src/auth-storage.ts:` `#disableDefinitiveOAuthFailure` (5089–5140) + failure branch of `#tryOAuthCredential` (5485–5523) + transient block constant `OAUTH_REFRESH_FAILURE_BACKOFF_MS = 5 * 60 * 1000` (:713) + classification re-exported from `./error/auth-classify` (:740).
**Signature:** `#disableDefinitiveOAuthFailure(provider, credentialId|undefined, attemptedCredential, index, errorMsg): Promise<"disabled" | "peer-rotated" | "cas-lost">`.
**Data Shape:** Outcomes: definitive (invalid_grant, revoked, 401/403 not from network blip) ⇒ CAS-disable + tombstone with verbatim cause + `credential_disabled` event; transient (network/5xx/timeout) ⇒ 5-minute temp block, row kept.

### Decisive source
```ts
// peer-rotation pre-check BEFORE the disable:
if (latestCredential?.type === "oauth" && latestCredential.refresh !== attemptedCredential.refresh) {
	await this.reload();
	return "peer-rotated";   // Anthropic rotates refresh tokens on EVERY use —
}                            // the peer's success leaves our stored token invalid
const disabled =
	credentialId !== undefined
		? this.#disableCredentialByIdIfMatches(
				provider,
				credentialId,
				attemptedCredential,
				`oauth refresh failed: ${errorMsg}`,
			)
		: this.#tryDisableCredentialAtIfMatches(
				provider,
				index,
				attemptedCredential,
				`oauth refresh failed: ${errorMsg}`,
			);
if (!disabled) {
	await this.reload();
	return "cas-lost";
}
return "disabled";
```

**Flow:** refresh error → stringify → `AIError.isDefinitiveOAuthFailure(msg)`; definitive ⇒ peer check → CAS-disable (conditioned on persisted data still matching the ATTEMPTED credential) → emit event (buffered up to 32 while no listener). Transient ⇒ mark blocked for 5 min so selection skips it. Preflight failures during candidate preparation skip those candidates in the final pass but MUST disable on definitive (not merely block), else the row is retried forever (:4962–4967 comment). The auth-retry policy wrapper (`resolver()` :6530–6555): initial resolve → step (b) force-refresh SAME account → step (c) rotate to sibling.
**Invariant:** Only DEFINITIVE failures tear rows down; blocking-on-transient must never soft-delete (a flaky network would log the user out). Every disable is CAS'd against the attempted bytes because a concurrent login/peer rotation may have just replaced the dead token. Disabled rows keep identity-only tombstones (`DisabledCredentialSummary`) so auto-disabled accounts stay visible in UI instead of vanishing silently.
**Probe:** `packages/ai/test/auth-storage-oauth-refresh-race.test.ts` — `still disables when the failure is real (no concurrent rotation)` (:177); `oauth-definitive-failure.test.ts`; `auth-storage-credential-disabled-event.test.ts` (event buffering/replay).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "disableDefinitiveOAuthFailure", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-outcome taxonomy and CAS-disable-with-tombstone pattern; adapt the definitive-failure regex to host providers' actual error strings; omit the specific event-buffer cap. Treating any refresh failure as permanent is the classic wrong port.
