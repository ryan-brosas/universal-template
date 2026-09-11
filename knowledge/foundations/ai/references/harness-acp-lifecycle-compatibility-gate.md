<!-- capsule-v2 -->
# ACP lifecycle compatibility gate — what must match before persisted session state may be reused?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** Which identities does a resumed session validate before attaching, and how do you stay forward-compatible with legacy state that predates your flags?

## Four-identity pre-attach validation
**Path/Symbol:** `packages/harness-acp/src/v1/acp-v1-lifecycle.ts` — `validateACPLifecycleCompatibility` (:69–115), `shouldMaterializeACPSkills` (:48–67), `resolveACPInitialGuidanceApplied` (:37–46); invoked from `acp-v1-harness.ts:330–339` and `:342–346`.
**Signature:** `validateACPLifecycleCompatibility({ harnessId, lifecycleHarnessId, implementationIdentity, authenticationProfile, lifecycleData, sandboxId }): void`.
**Data Shape:** `ACPLifecycleData = ACPPromptGuidanceLifecycleState & { implementationIdentity: string; authenticationProfile?: {digest}; acpSessionId?; bridge?; coldSession?; turnStartConfig?; recovery?; restoration? }`.

### Decisive source
```ts
// acp-v1-lifecycle.ts:84–114 — every identity mismatch is a hard throw BEFORE attach
if (lifecycleHarnessId !== harnessId) {
  throw new Error(`ACP lifecycle state was produced by harness ${JSON.stringify(lifecycleHarnessId)}, but this harness is ${JSON.stringify(harnessId)}.`);
}
if (lifecycleData.implementationIdentity !== implementationIdentity) {
  throw new Error('ACP lifecycle state is incompatible with the configured implementation.');
}
if (lifecycleData.authenticationProfile?.digest !== authenticationProfile.digest) {
  throw new Error('ACP lifecycle state is incompatible with the configured authentication profile.');
}
const expectedSandboxId = lifecycleData.bridge?.sandboxId;
if (expectedSandboxId != null && sandboxId != null && expectedSandboxId !== sandboxId) {
  throw new Error(`ACP lifecycle state belongs to sandbox ${JSON.stringify(expectedSandboxId)}, not ${JSON.stringify(sandboxId)}.`);
}
// :57–66 — a changed skill set throws even when prior materialization never completed
if (isResume && lifecycleState?.skillsFingerprint != null && lifecycleState.skillsFingerprint !== skillsFingerprint) {
  throw new Error('ACP lifecycle state was created with a different set of skills.');
}
return !isResume || lifecycleState?.skillsMaterialized !== true;
```

**Flow:** `doStart` computes the CURRENT implementationIdentity + authenticationProfile digest from live settings → if resume/continue state exists, run the four checks (harness id string; implementation digest; auth-profile digest; sandbox id ONLY when both sides carry one) → then `shouldMaterializeACPSkills` decides whether skill files must be re-materialized in the sandbox → `resolveACPInitialGuidanceApplied` seeds whether `<session-guidance>` was already announced. Sandbox-id check is deliberately two-sided-null-tolerant: unknown-on-either-side skips rather than fails.
**Invariant:** reuse requires proof of identity equivalence, not structural validity (a structurally valid payload from a differently-configured harness still throws); legacy states missing boolean flags default to ALREADY-applied/materialized so upgrades never re-inject guidance or re-copy skills into a continued conversation.
**Probe:** direct tests `packages/harness-acp/src/v1/acp-v1-lifecycle.test.ts:98–167` (accept-match + `it.each` rejection of harness/implementation/auth-profile/sandbox mismatches), `:37–95` (guidance defaults for fresh vs legacy-resume vs explicit-flag; skill re-materialization skipped on matching fingerprint, thrown on changed fingerprint even with `skillsMaterialized:false`) and `packages/harness-acp/src/acp-harness.test.ts:3597–3658` ("validates lifecycle state structurally and rejects incompatible identities at start" — schema-validates OK but `doStart` rejects with 'incompatible with the configured implementation').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "validateACPLifecycleCompatibility shouldMaterializeACPSkills resolveACPInitialGuidanceApplied", limit: 10 });
```

## Verdict
Adopt digest-based identity gating over structural schema validation for any cross-process session state — the schema admits payloads the runtime must still reject; adapt the four identities to your host's equivalent axes; omit ACP skill materialization specifics. Caveat: none — both unit file and adapter-level behavior are pinned.
