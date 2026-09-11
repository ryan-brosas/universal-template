<!-- capsule-v2 -->
# GitHub Transport Error Sanitation — how do you classify subprocess/HTTP failures into actionable errors without leaking tokens or raw output?

**Source:** shadcn-ui UNLICENSED `main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`; Codebase Memory `shadcn-ui`. **Question:** A transport layer mixes REST calls (carrying a bearer token) and a CLI subprocess (whose stderr embeds secrets and private paths) — what error shape keeps messages useful while provably leak-free?

## sanitized-kind transport error + fixed-string guidance table
**Path/Symbol:** `packages/shadcn/src/registry/github-cli.ts:GitHubTransportError` (:34-47), `getEnvGitHubToken` (:49-58), `fetchGitHubApi` (:108-130), `classifyGhFailure` (:193-227), `getGitHubTransportFailureGuidance` (:292-389).
**Signature:** `new GitHubTransportError(kind: "http"|"network"|"timeout"|"enoent"|"unauthenticated"|"oversize"|"invalid-response", { statusCode?, message? })`; `classifyGhFailure(error): GitHubTransportError`; `getGitHubTransportFailureGuidance(error, mode): { detail, suggestion }`.
**Data Shape:** The error carries ONLY `kind` and a range-validated `statusCode`. Guidance is a closed lookup over kind(+mode for credential variants: token vs gh wording) with hardcoded strings.

### Decisive source
```ts
// Internal transport failure carrying only sanitized, validated fields. Raw
// subprocess or response output must never be attached to it.
export class GitHubTransportError extends Error { ... }

// classify from execa failure — regex, validate, then DISCARD the stderr:
if (/gh auth login|not logged in/i.test(stderr))
  return new GitHubTransportError("unauthenticated")
const statusMatch = stderr.match(/\(HTTP (\d{3})\)/)
if (statusMatch) {
  const statusCode = Number(statusMatch[1])
  if (statusCode >= 100 && statusCode <= 599)
    return new GitHubTransportError("http", { statusCode })
}
return new GitHubTransportError("network")

// fetch failure: "The underlying error may embed request details, so it is
// dropped and replaced with a fixed-string failure."
throw new GitHubTransportError("network")

// Token gating BEFORE it can enter any header:
const HEADER_SAFE_TOKEN_PATTERN = /^[\x21-\x7E]+$/   // printable ASCII, no ws
```

**Flow:** every transport failure is first squeezed into `{kind, statusCode?}` — network throws are replaced by fixed-string errors, gh stderr is pattern-matched (auth-login phrasing → unauthenticated; `(HTTP nnn)` with 100–599 → http) and then thrown away; user-facing detail/suggestion strings come exclusively from `getGitHubTransportFailureGuidance`, keyed by kind and auth mode (401/403/429/5xx have distinct copy). Tokens are read GH_TOKEN→GITHUB_TOKEN through the registry-context env (injected env REPLACES process.env), trimmed, and rejected outright unless they match the header-safe printable-ASCII pattern; an unsafe first candidate falls through to the next env var.
**Invariant:** No byte of a response body, subprocess stdout/stderr, or underlying error message may survive into the thrown error's message, stack, or properties — the test literally injects a secret into all three channels and asserts it appears nowhere in the rendered error. Status codes must be range-checked before storage. Tokens must never contain whitespace/control characters.
**Probe:** `packages/shadcn/src/registry/github-cli.test.ts` — :230-257 secret planted in fake message+stderr+stdout must not appear in JSON.stringify(error); :308-328 401 response does not echo `super-secret-token`; :176-228 classification matrix (enoent/timeout/unauthenticated/(HTTP 404)/unknown); :56-105 token precedence, trim, unsafe-fallback, context-env isolation. Runner caveat: node_modules absent in checkout — pinned by direct reads.
**Coverage:** github-cli.ts `no_recorded_issue` @ generation 2026-08-25T20:00:37Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "shadcn-ui", query: "GitHubTransportError sanitized kind statusCode fixed-string failure guidance", limit: 8 });
// observed: getGitHubTransportFailureGuidance #1 (:292-389), GitHubFailureKind #2,
// constructor #3, classifyGhFailure #6, class #7
```

## Verdict
Adopt the two-channel split (machine-readable sanitized kind/statusCode on the error; human guidance from a static table selected by kind+mode) plus regex-and-discard stderr classification and the printable-ASCII token gate for any client that shells out to authenticated CLIs. Adapt the kind vocabulary and guidance copy to your transports. Omit the specific GH_* env scrubbing here if you use the dedicated hermetic-env capsule instead.
