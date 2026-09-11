<!-- capsule-v2 -->
# Settings account lifecycle — how should a settings page drive an OAuth account through provider routes with popup-first sign-in and state-specific polling?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how does a browser page keep sign-in/sign-out/quota states truthful — including a blocked popup, an untrusted remote origin, and reauth-required — without inventing a state the server did not report?

## Seven-state account projection
**Path/Symbol:** `src/client/OpenAICodexSettings.tsx:22-29 AccountStatus`, `:19-20 POLL_INTERVAL_MS`+`USAGE_POLL_INTERVAL_MS`, `:271-279 refresh`, `:300-307 poll effect`, `:309-329 signIn`, `:331-341 signOut`, `:269 trustedOriginCommand`, `:386-395 copyTrustedOriginCommand`.
**Signature:** `type AccountStatus = { status: 'loading' } | { status: 'signed-out' } | { status: 'signing-in' } | { status: 'reauth-required'; message: string } | { status: 'signed-in'; usage: OpenAICodexUsage; quotaError?: string } | { status: 'remote-web-origin-not-trusted' } | { status: 'error'; message: string }`; `signIn(): Promise<void>`; `signOut(): Promise<void>`.
**Data Shape:** the union mirrors exactly what `GET /plugins/dsh-openai-codex/auth/status` can return (the server-side ladder mined in `auth-status-recovery`); quota failure rides inside signed-in as `quotaError?` instead of demoting authentication.

### Decisive source
```ts
const POLL_INTERVAL_MS = 1_000          // while signing-in
const USAGE_POLL_INTERVAL_MS = 60_000   // while signed-in

useEffect(() => {
  const interval = status.status === 'signing-in'
    ? POLL_INTERVAL_MS
    : status.status === 'signed-in' ? USAGE_POLL_INTERVAL_MS : undefined
  if (interval === undefined) return
  const timer = window.setInterval(() => { void refresh() }, interval)
  return () => { window.clearInterval(timer) }
}, [refresh, status.status])

const signIn = async (): Promise<void> => {
  const popup = window.open('about:blank', '_blank')   // BEFORE any await:
  if (popup !== null) popup.opener = null              // popup blockers need the
  setBusy(true)                                        // user gesture
  setStatus({ status: 'signing-in' })
  try {
    const challenge = await jsonRequest<LoginChallenge>(LOGIN_PATH, 'POST')
    if (popup === null) { setStatus({ status: 'error', message: t('popupBlocked') }); return }
    popup.location.replace(challenge.url)
  } catch (error) {
    popup?.close()
    setStatus(error instanceof AccountRequestError && error.code === 'remote-web-origin-not-trusted'
      ? { status: 'remote-web-origin-not-trusted' }
      : { status: 'error', message: error instanceof Error ? error.message : t('requestFailed') })
  } finally { setBusy(false) }
}
```

**Flow:** mount → one `refresh()` GET of the status route → render from the union (status dot + label + action button chosen per state) → user clicks login: popup opens synchronously, opener severed, POST login returns `{ url }`, popup navigates to the provider challenge, page polls status every 1 s until the browser flow settles server-side → signed-in switches polling to 60 s usage refreshes; logout POSTs and locally projects `signed-out` only on ok.
**Invariant:** every UI state is a projection of a server-reported state — nothing is guessed; the two special error codes (`remote-web-origin-not-trusted`) get their own union member and a remediation card (`dsh plugin --profile web exec dsh-openai-codex trust-origin <origin>`, origin taken from `window.location.origin`, copied via clipboard when available) instead of a generic failure; the popup is opened before the first await so ad-blockers cannot eat the user gesture, and is closed again if the challenge request fails; intervals exist only for the two states that need them and are cleared on change.
**Probe:** `tests/openai-codex-settings.client.spec.tsx` pins the model-catalog slice end-to-end (checkbox render, POST body `{ models: ['gpt-5.6-sol'] }` preserving provider order). Caveat recorded honestly: the sign-in/sign-out/polling paths have no dedicated spec file; their evidence is this direct source read plus the server-side ladders already pinned by `tests/auth-routes.spec.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: '^dsh-codex\\.src\\.client\\.OpenAICodexSettings\\.(signIn|signOut|AccountRequestError|formatOpenAICodexResetAt)$', limit: 10 });
```
Executed live against project `dsh-codex`: total 4, has_more false (`AccountRequestError` Class 229-234, `formatOpenAICodexResetAt` Function 127-132, `signIn` Function 309-329, `signOut` Function 331-341). Graph note: trace_path on `refresh` merges this module's useCallback refresh with QuotaIndicator's inner refresh into one node — they are distinct closures in source.

## Verdict
Adopt the closed AccountStatus union plus popup-before-await sign-in and state-gated poll intervals; adopt "special error codes become named states with remediation copy." Adapt route paths, the challenge hand-off (redirect vs postMessage), and the remediation command to your host. Omit client-side guessing of auth state between polls, and never let a quota fetch failure flip the account to signed-out. Coverage: `src/client/OpenAICodexSettings.tsx` and its spec are `no_recorded_issue` + `metadata_match`; sign-in/out paths lack a dedicated spec (recorded caveat).
