<!-- capsule-v2 -->
# TUI login controller — how does a terminal command start a browser OAuth login in the background, return a usable message immediately, and cancel without confusing logout with teardown?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** a chat-TUI `/login` must hand control back to the user at once while a system-browser OAuth flow runs unattended — what state machine keeps challenge delivery, cancellation, and credential deletion straight?

## TuiLoginController
**Path/Symbol:** `src/tui.ts:137-219 LoginState + TuiLoginController`, helpers `src/tui.ts:106-113 waitForPromptAbort`.
**Signature:** `new TuiLoginController(service: OpenAICodexService)` with `start(): Promise<string>`, `status(): LoginState`, `logout(): Promise<void>`, `dispose(): Promise<void>`; private `begin()`, `onEvent(event: AuthEvent)`.
**Data Shape:** `LoginState = { status:'idle' } | { status:'signing-in' } | { status:'error'; message:string }`. Five private handles move together: `operation` (the login promise), `cancellation` (AbortController), `challenge` (pending message promise) plus its `resolveChallenge`/`rejectChallenge` pair.

### Decisive source
```ts
async start(): Promise<string> {
  const stored = await this.service.authStatus()
  if (stored.authenticated) return 'OpenAI Codex is already signed in.'
  if (this.operation === undefined) this.begin()
  const challenge = this.challenge
  if (challenge === undefined) throw new Error('OpenAI Codex sign-in did not create an authorization challenge')
  return await challenge
}

private begin(): void {
  const cancellation = new AbortController()
  this.cancellation = cancellation
  this.state = { status: 'signing-in' }
  this.challenge = new Promise<string>((resolve, reject) => {
    this.resolveChallenge = resolve
    this.rejectChallenge = reject
  })
  this.operation = this.service.login({
    signal: cancellation.signal,
    prompt: prompt => prompt.type === 'select'
      ? Promise.resolve('browser')
      : waitForPromptAbort(prompt),
    notify: event => { this.onEvent(event) },
  }).then(
    () => { this.state = { status: 'idle' } },
    (error: unknown) => {
      const message = safeMessage(error)
      this.state = { status: 'error', message }
      this.rejectChallenge?.(error)
    },
  ).finally(() => {
    this.operation = undefined
    this.cancellation = undefined
    this.resolveChallenge = undefined
    this.rejectChallenge = undefined
  })
}

function waitForPromptAbort(prompt: AuthPrompt): Promise<string> {
  const signal = prompt.signal
  if (signal === undefined) return new Promise<string>(() => {})
  if (signal.aborted) return Promise.reject(signal.reason)
  return new Promise<string>((_resolve, reject) => {
    signal.addEventListener('abort', () => { reject(signal.reason) }, { once: true })
  })
}
```

**Flow:** `/codex login` → `start()` short-circuits on an already-authenticated store → otherwise single-flights via `operation === undefined` guard and awaits the *challenge* promise, not the login operation → provider emits `auth_url` → `onEvent` opens the browser and resolves every current waiter with either "opened" or the manual-open URL text → the login promise itself only updates terminal state (`idle` on success; redacted error state + reject pending challengers on failure) and its `finally` clears all five handles so the next `start()` begins fresh.
**Invariant:** exactly one background operation per controller (the `undefined` guard is the single-flight); the select prompt is answered `'browser'` synchronously so the flow never blocks on a human; non-select prompts never resolve — they wait forever unless aborted (`waitForPromptAbort` returns a never-settling promise when no signal exists, rejects immediately for an already-aborted signal, else listens `{once:true}`); logout cancels, awaits quiescence swallowing the abort error, THEN deletes the credential and resets to idle; dispose cancels and awaits quiescence but never deletes credentials (teardown ≠ sign-out); a failure path both persists the error state for later `/codex status` reads and rejects outstanding challenge waiters.
**Probe:** `tests/tui.spec.ts` pins the consumed service contract with a structural fake whose `login` resolves immediately; direct source read of :106-219 confirms the state machine above. Honest caveat: the controller's own async paths (challenge resolution, logout-cancel ordering, dispose-without-delete) have no dedicated spec — evidence is the complete source read plus the two registration/handler tests in the same file.
**Graph caveat recorded:** trace_path reports `TuiLoginController` callees = 0 because provider calls dispatch through the injected service; the single graphed caller is `registerCodexCommand` (source wins).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.tui\\.TuiLoginController\\.(start|begin|onEvent|logout|dispose)$', limit: 10 });
```
Executed live against project `dsh-codex`: total 5, has_more false. `get_code_snippet(dsh-codex.src.tui.TuiLoginController.start)` served lines 153-160 byte-matching the pinned checkout.

## Verdict
Adopt the split between a fast challenge-message promise and the slow login operation, synchronous select-prompt answering, and the logout/dispose asymmetry (delete vs preserve). Adapt the trigger surface (chat command vs CLI vs API), the challenge text, and where error state is observed. Omit resolving prompts by queueing UI callbacks into the OAuth flow — the controller converts prompts into promises up front. Coverage: src/tui.ts and tests/tui.spec.ts are `no_recorded_issue` + `metadata_match`.
