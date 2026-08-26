<!-- capsule-v2 -->
# Auth status recovery — preserve signed-in state across quota and browser-flow failures

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how can a web auth surface distinguish signed-out, reauth-required, and temporary quota failures without logging out a valid credential or leaking provider diagnostics?

## OpenAICodexWebAuth.status, readStoredStatus, and start error recovery
**Path/Symbol:** `src/auth-routes.ts:124-129 OpenAICodexWebAuth.status`, `src/auth-routes.ts:184-196 OpenAICodexWebAuth.start`, `src/auth-routes.ts:226-237 OpenAICodexWebAuth.readStoredStatus`.
**Signature:** `status(): Promise<OpenAICodexWebAuthStatus>`; private `readStoredStatus(): Promise<OpenAICodexWebAuthStatus>`.
**Data Shape:** Public status is a closed union: `signed-out`, `signing-in`, `signed-in` with `usage` and optional `quotaError`, `reauth-required` with a fixed message, or `error` with a bounded safe message. Quota failure uses an empty `rateLimits` projection rather than erasing authentication.

### Decisive source
```ts
private async readStoredStatus(): Promise<OpenAICodexWebAuthStatus> {
  const stored = await openAICodexAuthStatus(this.store)
  if (!stored.authenticated) return { status: 'signed-out' }
  try {
    return { status: 'signed-in', usage: await readOpenAICodexRateLimits(this.store) }
  } catch (error: unknown) {
    if (isOpenAICodexReauthRequiredError(error)) {
      return { status: 'reauth-required', message: OPENAI_CODEX_REAUTH_REQUIRED_MESSAGE }
    }
    return { status: 'signed-in', usage: { rateLimits: [] }, quotaError: safeMessage(error) }
  }
}

// A failed browser flow rechecks durable state before publishing the error.
const stored = await this.readStoredStatus()
if (stored.status === 'signed-in') { this.state = stored; return }
```

**Flow:** idle `status` reads the store projection; authenticated state attempts quota retrieval; the fixed reauth error becomes `reauth-required`; other usage failures preserve `signed-in` with empty rate limits and a redacted diagnostic; a failed browser login rechecks stored state before publishing its own error.
**Invariant:** quota availability is not authentication truth; a 401/403 reauth condition is explicit and does not trigger logout or a new login; transient usage errors cannot mask a valid stored credential; all surfaced diagnostics pass the token-redacting bounded formatter.
**Probe:** `tests/auth-routes.spec.ts:395-435` (failed browser flow restores stored sign-in, reauth-required does not call logout/login, and temporary usage failure returns signed-in + quotaError). The test range was directly read; only importOriginal line 40 is parse-partial.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.auth-routes\\.OpenAICodexWebAuth\\.(status|start|readStoredStatus)', limit: 10, fields: ['signature', 'name', 'file'] });
```

## Verdict
Adopt the closed status union and the recheck-before-error recovery ladder. Adapt the quota source and fixed reauth code/message; keep authentication and quota failure as separate state dimensions. Omit auto-logout on usage failure unless the provider explicitly proves the credential invalid. Coverage: `src/auth-routes.ts` is `no_recorded_issue` + `metadata_match`; `tests/auth-routes.spec.ts` is partial only at line 40, outside the cited direct assertions.
