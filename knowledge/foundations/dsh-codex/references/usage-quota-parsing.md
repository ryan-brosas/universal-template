<!-- capsule-v2 -->
# Usage quota — secret-free rate-limit parsing and reauthorization contract

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how to project a provider quota/usage response into a small secret-free object safe to expose to a browser, while failing closed on malformed values and surfacing a fixed, credential-free reauthorization error?

## parseOpenAICodexUsage + OpenAICodexReauthRequiredError
**Path/Symbol:** `src/usage.ts:parseOpenAICodexUsage` (187-217), `src/usage.ts:parseWindow` (111-128), `src/usage.ts:parseResetAt` (96-109), `src/usage.ts:parseCredits` (146-161), `src/usage.ts:parseIndividualLimit` (163-180), `src/usage.ts:OpenAICodexReauthRequiredError` (34-44), `src/usage.ts:readOpenAICodexRateLimits` (225-262).
**Signature:** `parseOpenAICodexUsage(value: unknown): OpenAICodexUsage`; `readOpenAICodexRateLimits(store: OpenAICodexCredentialStore): Promise<OpenAICodexUsage>`; `new OpenAICodexReauthRequiredError()`.
**Data Shape:** Input is opaque JSON from the ChatGPT `wham/usage` endpoint. Output `OpenAICodexUsage` = `{ rateLimits: OpenAICodexRateLimit[], credits?: {unlimited, balance?}, individualLimit?: {limit, used, remaining, remainingPercent} }`. Each `OpenAICodexRateLimit` = `{ id, name?, windows: OpenAICodexRateLimitWindow[] }`; each window = `{ remainingPercent, windowSeconds, resetAt? }`. `remainingPercent = 100 - used_percent`. The reauth error carries a fixed `code = 'OPENAI_CODEX_REAUTH_REQUIRED'` and a fixed message, no credential/account/response data.

### Decisive source
```ts
// src/usage.ts — secret-free quota projection
export function parseOpenAICodexUsage(value: unknown): OpenAICodexUsage {
  if (!isRecord(value)) throw new Error('OpenAI Codex returned a malformed usage response')
  const limits: OpenAICodexRateLimit[] = []
  const primary = parseLimit('codex', 'Codex', value['rate_limit'])
  if (primary !== undefined) limits.push(primary)
  const additional = value['additional_rate_limits']
  if (additional !== undefined && additional !== null && !Array.isArray(additional)) {
    throw new Error('OpenAI Codex returned malformed additional rate limits')
  }
  for (const item of additional ?? []) {
    if (!isRecord(item)) throw new Error('OpenAI Codex returned a malformed additional rate limit')
    const id = item['metered_feature']
    const name = item['limit_name']
    if (typeof id !== 'string' || id.length === 0) {
      throw new Error('OpenAI Codex returned an additional rate limit without an id')
    }
    // ... validate name, parseLimit(id, name, item['rate_limit'])
  }
  return {
    rateLimits: limits,
    ...credits === undefined ? {} : { credits },
    ...individualLimit === undefined ? {} : { individualLimit },
  }
}

// Fail-closed window parsing: percent bounded 0..100, window seconds positive int
function parseWindow(value: unknown): OpenAICodexRateLimitWindow | undefined {
  if (value === undefined || value === null) return undefined
  if (!isRecord(value)) throw new Error('OpenAI Codex returned a malformed rate-limit window')
  const usedPercent = value['used_percent']
  const windowSeconds = value['limit_window_seconds']
  if (typeof usedPercent !== 'number' || !Number.isFinite(usedPercent) || usedPercent < 0 || usedPercent > 100) {
    throw new Error('OpenAI Codex returned an invalid used percentage')
  }
  if (typeof windowSeconds !== 'number' || !Number.isInteger(windowSeconds) || windowSeconds <= 0) {
    throw new Error('OpenAI Codex returned an invalid rate-limit window duration')
  }
  const resetAt = parseResetAt(value)
  return { remainingPercent: 100 - usedPercent, windowSeconds, ...resetAt === undefined ? {} : { resetAt } }
}

// Secret-free reauthorization error: no response, credential, or account data
export class OpenAICodexReauthRequiredError extends Error {
  readonly code = OPENAI_CODEX_REAUTH_REQUIRED_CODE
  constructor() {
    super(OPENAI_CODEX_REAUTH_REQUIRED_MESSAGE)
    this.name = 'OpenAICodexReauthRequiredError'
  }
}
```

**Flow:** validate top-level record → parse primary `rate_limit` bucket (id `codex`) → parse each `additional_rate_limits` item (id from `metered_feature`) → parse optional `credits` and `spend_control.individual_limit` → return the secret-free projection. `readOpenAICodexRateLimits` fetches the fixed `OPENAI_CODEX_USAGE_URL` with refreshed plugin credentials (`Bearer` access + `chatgpt-account-id`), and on HTTP 401/403 throws `OpenAICodexReauthRequiredError`; on other non-OK throws a status-only error; unreadable JSON throws with `cause`.
**Invariant:** every numeric field is validated fail-closed (percent 0..100, window seconds positive integer, reset_at safe-integer within `Date` range); a null/absent optional field is dropped without failing the whole parse; the reauth error never leaks a secret (fixed message, no response body, no credential, no account id).
**Probe:** `tests/usage.spec.ts` — "projects rolling percentages and exact provider-supported balances", "rejects percentages that would make a quota bar misleading", "projects a valid WHAM reset_at without deriving a client-side timestamp", "treats an explicit null reset_at as unavailable", `it.each(['1735689600', 0, -1, 1.5, Number.MAX_SAFE_INTEGER])` "fails closed when reset_at is present but invalid", "reads the fixed usage endpoint with refreshed plugin credentials", `it.each([401, 403])` "throws a secret-free reauthorization error", and "keeps a signed-in account usable when quota metadata is unavailable".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-codex", query: "usage rate limit quota parse remaining percent", limit: 15, fields: ["signature", "lines"] });
```

## Verdict
Adopt the fail-closed quota parser (`parseOpenAICodexUsage` and its window/credit/limit helpers) and the fixed-message reauthorization error as a portable, secret-free contract for exposing provider quota to a browser. Adapt the endpoint URL, the `Bearer`/`chatgpt-account-id` header shape, and the specific `metered_feature` ids to the target provider. Omit the `pi-ai` `createModels`/`openaiCodexProvider` credential-refresh plumbing and the `OPENAI_CODEX_PROVIDER` constant when porting to another provider. Coverage: `src/usage.ts` and `tests/usage.spec.ts` both `no_recorded_issue` + `metadata_match`; the vitest runner is not installed in this read-only checkout, so deterministic probes were executed against the actual source (Node strip-types) and matched every test assertion (full projection, reject 101%, valid/null/invalid reset_at, reauth code + secret-free).
