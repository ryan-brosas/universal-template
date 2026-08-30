<!-- capsule-v2 -->
# claude.ai proxy fetch retry ladder — why must the retry decision compare the token that was SENT, not the token on disk?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How do I retry proxy-connector 401s exactly once without mass-marking 30 healthy connectors needs-auth?

## Sent-token capture + changed-token gating + stale-response fallback
**Path/Symbol:** `src/services/mcp/client.ts`:`createClaudeAiProxyFetch` (:372-422); header injection `'X-Mcp-Client-Session-Id': getSessionId()` (:895).
**Signature:** `createClaudeAiProxyFetch(innerFetch: FetchLike): FetchLike`.
**Data Shape:** Returns `{response, sentToken}` from the request closure; retry fires only when `handleOAuth401Error(sentToken)` returns true (token actually rotated) or the keychain now holds a different token.

### Decisive source
```ts
const doRequest = async () => {
  await checkAndRefreshOAuthTokenIfNeeded()
  const currentTokens = getClaudeAIOAuthTokens()
  if (!currentTokens) throw new Error('No claude.ai OAuth token available')
  headers.set('Authorization', `Bearer ${currentTokens.accessToken}`)
  const response = await innerFetch(url, { ...init, headers })
  // Return the exact token that was sent. Reading getClaudeAIOAuthTokens()
  // again after the request is wrong under concurrent 401s: another
  // connector's handleOAuth401Error clears the memoize cache, so we'd read
  // the NEW token from keychain, pass it to handleOAuth401Error, which
  // finds same-as-keychain → returns false → skips retry.
  return { response, sentToken: currentTokens.accessToken }
}
...
if (!tokenChanged) {
  // ELOCKED contention: another connector may have won the lockfile and refreshed — check if token changed underneath us
  const now = getClaudeAIOAuthTokens()?.accessToken
  if (!now || now === sentToken) return response      // genuinely-stale credential: give up WITHOUT caching needs-auth here
}
try { return (await doRequest()).response }
catch { return response }   // retry network failure → original 401 for outer classification
```

**Flow:** request → proactive token refresh → attach bearer → on 401 ask whether the token ROTATED (sent vs keychain) → rotated ⇒ one retry; unchanged ⇒ return the 401 (outer handler decides needs-auth) — this prevents one stale token from sticking 30+ connectors into the 15-min needs-auth cache (comment :366-371).
**Invariant:** The token passed to the retry-decision helper MUST be captured before the request and returned alongside it; re-reading current tokens after await conflates "my token was stale" with "someone else already refreshed".
**Probe:** `grep -n 'return { response, sentToken: currentTokens.accessToken }' src/services/mcp/client.ts` (`390:`) and `grep -n 'const tokenChanged = await handleOAuth401Error(sentToken)' src/services/mcp/client.ts` (`402:`) and `grep -n 'X-Mcp-Client-Session-Id' src/services/mcp/client.ts` (`895:`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createClaudeAiProxyFetch", limit: 5 });
```

## Verdict
Adopt sent-token capture and change-gated single retry for any shared-credential connector fleet. Adapt the upstream refresh primitives (checkAndRefreshOAuthTokenIfNeeded/handleOAuth401Error equivalents). Omit claude.ai-specific proxy URL construction.
