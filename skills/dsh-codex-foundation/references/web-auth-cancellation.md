<!-- capsule-v2 -->
# Web auth cancellation — drain provider work before logout or disposal

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how should a browser auth owner cancel an in-flight provider operation, settle every challenge waiter, and guarantee logout deletes credentials only after the operation is quiescent?

## OpenAICodexWebAuth.signOut, dispose, and cancelSignIn
**Path/Symbol:** `src/auth-routes.ts:141-153 OpenAICodexWebAuth.signOut/dispose` and `src/auth-routes.ts:239-253 rejectChallenge/clearChallengeTimer/cancelSignIn`.
**Signature:** `signOut(): Promise<void>`; `dispose(): Promise<void>`; private `cancelSignIn(error: Error): void`.
**Data Shape:** The coordinator owns an `AbortController` for provider work, a `Promise<void>` operation, a queue of `{ resolve, reject }` challenge waiters, and a public status. `signOut` cancels and drains then deletes; `dispose` cancels and drains but does not delete.

### Decisive source
```ts
async signOut(): Promise<void> {
  this.cancelSignIn(new Error('OpenAI Codex sign-in cancelled'))
  await this.operation?.catch(() => undefined)
  await logoutOpenAICodex(this.store)
  this.challenge = undefined
  this.state = { status: 'signed-out' }
}

async dispose(): Promise<void> {
  this.cancelSignIn(new Error('OpenAI Codex plugin disposed'))
  await this.operation?.catch(() => undefined)
}

private cancelSignIn(error: Error): void {
  this.rejectChallenge(error)
  this.cancellation?.abort(error)
}
```

**Flow:** cancellation rejects and removes all pending challenge waiters, aborts the provider interaction, and lets the operation rejection settle; sign-out then invokes the owned logout adapter and resets public state; plugin disposal follows the same drain path without touching durable credentials. The operation `finally` block clears timers and ownership pointers.
**Invariant:** no credential deletion races an active provider login; every waiter gets a terminal rejection; `dispose` is safe to call for teardown, while `signOut` is the only path that guarantees signed-out state and credential deletion after quiescence.
**Probe:** `tests/auth-routes.spec.ts:313-345` (logout/dispose abort the observed signal, reject all waiters, and call mocked logout only for sign-out), plus `tests/auth-routes.spec.ts:372-393` (complete-flow timeout aborts after a challenge). The cited test ranges were read directly despite the unrelated parse-partial marker at line 40.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.auth-routes\\.OpenAICodexWebAuth\\.(signOut|dispose|cancelSignIn)', limit: 10, fields: ['signature', 'name', 'file'] });
```

## Verdict
Adopt the cancel → await quiescence → delete ordering and waiter fan-out. Adapt the abort/error type and provider operation; preserve the distinction between destructive sign-out and non-destructive disposal. Omit any implementation that deletes credentials before the provider operation has observed cancellation. Coverage: `src/auth-routes.ts` is `no_recorded_issue` + `metadata_match`; direct lifecycle assertions are in the partially flagged test file but outside its flagged line 40.
