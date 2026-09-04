<!-- capsule-v2 -->
# Context-window error classification — how do you detect "prompt too long" across providers without string-matching yourself into fragility?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** What predicate routes an API error into the context-management recovery path?

## checkContextWindowExceededError: three-vendor disjunction over status+message patterns
**Path/Symbol:** `src/core/context/context-management/context-error-handling.ts:3-95`.
**Signature:** `checkContextWindowExceededError(error: unknown): boolean` = OpenAI ∨ OpenRouter ∨ Anthropic checks; every branch try/catch-wrapped to `false`.

### Decisive source
```ts
// OpenAI-style: LengthFinishReasonError by NAME, else APIError + code 400 + substring
if (error.name === "LengthFinishReasonError") return true
const KNOWN_CONTEXT_ERROR_SUBSTRINGS = ["token", "context length"]
return error instanceof APIError && error.code?.toString() === "400"
    && KNOWN_CONTEXT_ERROR_SUBSTRINGS.some(s => error.message.includes(s))
// OpenRouter-style: status ?? code ?? error.status ?? response.status === "400"
//   AND regex family: /\bcontext\s*(?:length|window)\b/i, /\bmaximum\s*context\b/i,
//   /\b(?:input\s*)?tokens?\s*exceed/i, /\btoo\s*many\s*tokens?\b/i
// Anthropic-style: error.error.type === "invalid_request_error" AND pattern family:
//   prompt is too long / maximum.*tokens / context.*too.*long / exceeds.*context /
//   token.*limit / context_length_exceeded / max_tokens_to_sample
```

**Flow:** any thrown value enters; vendor-specific shapes are probed defensively (no property access without guards); a positive verdict hands the error to the request-stack retry policy (FORCED_CONTEXT_REDUCTION_PERCENT / MAX_CONTEXT_WINDOW_RETRIES — see request-stack-loop capsule), which then drives manageContext.
**Invariant:** Classification is total (never throws) and conservative-by-default (false on doubt); it inspects ERROR SHAPE only — no network retries here, that belongs to the caller.
**Probe:** No dedicated spec at this HEAD (coverage caveat) — pinned indirectly via request-loop overflow-retry specs in `src/core/task/__tests__/Task.spec.ts` context-window scenarios.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "checkContextWindowExceededError context length exceeded", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way defensive classifier as the SINGLE predicate feeding overflow recovery. Refresh the regex/substring families when you add vendors. Omit nothing — it is already host-free.
