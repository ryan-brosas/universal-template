<!-- capsule-v2 -->
# Web auth challenge — one login operation, validated HTTPS URL, settled waiters

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how can a browser-facing auth coordinator multiplex concurrent sign-in callers around one provider operation while exposing only a validated HTTPS authorization challenge and never leaving waiters pending?

## OpenAICodexWebAuth.signIn, start, and onEvent
**Path/Symbol:** `src/auth-routes.ts:132-138 OpenAICodexWebAuth.signIn`, `src/auth-routes.ts:155-203 OpenAICodexWebAuth.start`, `src/auth-routes.ts:205-224 OpenAICodexWebAuth.onEvent`.
**Signature:** `signIn(): Promise<LoginChallenge>`; private `start(): void`; private `onEvent(event: AuthEvent): void`.
**Data Shape:** `LoginChallenge = { url: string }`; private state is `signed-out | signing-in | signed-in | reauth-required | error`; one `operation: Promise<void>`, one `AbortController`, and an array of challenge waiter resolvers/rejecters are owned by the coordinator.

### Decisive source
```ts
async signIn(): Promise<LoginChallenge> {
  if (this.operation === undefined) this.start()
  if (this.challenge !== undefined) return this.challenge
  return new Promise((resolve, reject) => {
    this.challengeWaiters.push({ resolve, reject })
  })
}

private onEvent(event: AuthEvent): void {
  if (event.type !== 'auth_url') return
  const url = new URL(event.url)
  if (url.protocol !== 'https:' || url.username !== '' || url.password !== '') {
    this.cancelSignIn(new Error('OpenAI returned an unsafe authorization URL'))
    return
  }
  this.challenge = { url: event.url }
  this.clearChallengeTimer()
  for (const waiter of this.challengeWaiters.splice(0)) waiter.resolve(this.challenge)
}
```

**Flow:** first `signIn` starts the provider-native interaction and marks public state `signing-in`; later callers join the same operation; the first `auth_url` event is parsed and constrained to HTTPS without userinfo, clears the URL timer, and resolves all current waiters; the operation and callback timers are finally cleared when provider work settles.
**Invariant:** there is at most one provider login operation per coordinator; only a syntactically valid HTTPS URL without embedded credentials becomes a challenge; invalid/missing challenges reject waiters rather than leaving the browser status stuck in `signing-in`.
**Probe:** `tests/auth-routes.spec.ts:272-311` (concurrent callers share one operation and unsafe HTTP URLs abort it), plus `tests/auth-routes.spec.ts:347-393` (missing URL, URL timeout, and complete callback timeout settle/reject). The test file has only a parse-partial marker at line 40; the cited ranges were read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.auth-routes\\.OpenAICodexWebAuth\\.(signIn|start|onEvent)', limit: 10, fields: ['signature', 'name', 'file'] });
```

## Verdict
Adopt the single-flight challenge coordinator, waiter fan-out, HTTPS/userinfo validation, and bounded timers. Adapt the provider prompt/event vocabulary and cancellation primitive; keep PKCE/state/token exchange in the provider-native auth layer because this repository delegates it to `pi-ai` rather than implementing it in `auth-routes.ts`. Coverage: `src/auth-routes.ts` is `no_recorded_issue` + `metadata_match`; `tests/auth-routes.spec.ts` is `partial` only at the direct-import line 40 and was source-read around every cited assertion.
