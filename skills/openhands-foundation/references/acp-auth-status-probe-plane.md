<!-- capsule-v2 -->
# ACP auth-status probe plane — how do you detect "already logged in" on a host you only reach through an API, without lying when detection is impossible?

**Source:** OpenHands / All-Hands-AI (MIT) `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How should a GUI learn whether a provider CLI is authenticated on the agent-server host, and what may it claim when the probe cannot run?

## Per-provider status commands through the bash endpoint + honesty precedence ladder
**Path/Symbol:** `src/api/acp-service/acp-service.api.ts` (`ACP_AUTH_PROBES` :70–84, `classifyClaude/Codex/Gemini` :30–66, `getAuthStatus` :100–107); `src/hooks/query/use-acp-auth-status.ts` (:21–98); `src/utils/acp-auth-display.ts` (`resolveAcpAuthDisplay` :37–46); section consumer `acp-credentials-section.tsx` (:19–76).
**Signature:** `AcpService.getAuthStatus(server: string): Promise<"authenticated"|"unauthenticated"|"unknown">`; `useAcpAuthStatus(providerKey, { enabled? }) → { status, isChecking, isSupported }`.
**Data Shape:** queryKey `[acp-auth-status, backend.id, providerKey]`; `staleTime: Infinity` + `gcTime: 15 min` = one subprocess per provider per backend per window; `PROBE_TIMEOUT_SECONDS=10`.

### Decisive source
```ts
// acp-service.api.ts — Codex writes to stderr; match BOTH streams and check
// the NEGATIVE phrase first because it contains the positive substring.
function classifyCodex(out: BashOutput): AcpAuthStatus {
  const text = streams(out).toLowerCase();
  if (text.includes("not logged in")) return "unauthenticated";
  if (text.includes("logged in")) return "authenticated";
  return "unknown";
}
```
```ts
// acp-auth-display.ts — a stored credential NEVER reports as signed-in:
// only the probe can confirm an actual host login (#1244).
if (status === "authenticated") return "signed-in";
if (isChecking) return "checking";
if (credentialsConfigured) return "configured";
return "none";
```

**Flow:** probe registry keyed by provider id (claude `auth status --json` parsing `loggedIn` from JSON NOT exit code; codex phrase-matching both streams; gemini has no status command ⇒ `test -f ~/.gemini/oauth_creds.json && echo present || echo absent` matched on trimmed STDOUT only so a shell warning can't flip a real result) → anything unclassifiable (CLI missing, odd output, bash failure, unknown provider) collapses to `"unknown"` — probeAcpAuth catches EVERYTHING so a dead endpoint shows API-key fields instead of a false "not logged in" → hook gates on LOCAL backends only (CLIs live where the server runs); cloud ⇒ skip with `isSupported:false, isChecking:false` so consumers fall straight to the credential signal without spinning → banner precedence signed-in > checking > configured(stored secret) > none. Credential notion is provider-generic: a `CODEX_AUTH_JSON` blob counts as configured; a base-URL secret does not.
**Invariant:** Detection failure must be indistinguishable from "no data", never from "logged out". Only a successful host-side probe may claim signed-in. The probe runs a subprocess ⇒ cache aggressively, gate to visibility (`enabled`) so mounting-all-slides onboarding doesn't spawn processes early.
**Probe:** `__tests__/hooks/query/use-acp-auth-status.test.tsx` (136 L) — reject→unknown not "unauthenticated" (:67–78), cloud gate never probes nor spins (:91–110), credential-less OAuth providers still probed (:112–124); `acp-credentials-section.test.tsx` (201 L) configured-vs-detected arms incl. base-URL-doesn't-count (:145–179); `acp-credentials-section-cloud.test.tsx` (116 L) drives the REAL SecretsService cloud branch by mocking only its `fetchCloudSecrets` boundary (#1244).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "acp auth status probe classify provider login", limit: 10 });
```

## Verdict
Adopt the three-valued verdict with catch-all→unknown, local-only gating, per-provider command registry with output classifiers, and the four-state display precedence where stored credentials can't impersonate logins. Adapt the provider commands to your CLIs. Omit the bash-endpoint reuse if your server offers a first-class status endpoint. Coverage: no_recorded_issue on all five cited paths at gen 2026-08-24T16:13:32Z.
