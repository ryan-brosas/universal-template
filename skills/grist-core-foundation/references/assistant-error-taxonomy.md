<!-- capsule-v2 -->
# Assistant error taxonomy — which provider failures map to which user-facing messages, and when does the UI say "restart the conversation"?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** How are context_length_exceeded / finish_reason=length / insufficient_quota / generic failures classified, and why do first-vs-later message errors differ?

## _fetchCompletion classifies by errorCode + finish_reason; messages.length ≤ 2 splits First vs Later TokensExceeded
**Path/Symbol:** `app/server/lib/Assistant.ts`: error classes (:107–155) with exact user strings; `app/server/lib/OpenAIAssistantV1.ts`: classification (:217–238) — length gate :219–222, first/later split :224–228, quota :230–233, non-200 :234–238.
**Signature:** Hierarchy: `ApiError` → `NonRetryableError` → `TokensExceededError` → {First,Later}; `QuotaExceededError(503)`; `RetryableError extends Error`.
**Data Shape:** Codes carry client-side meaning: `{code: "ContextLimitExceeded"}` on 400s.

### Decisive source
```ts
const errorCode = result.error?.code;
if (errorCode === "context_length_exceeded" ||
    result.choices?.[0].finish_reason === "length") {     // ALSO a 200-response truncation!
  log.warn("AI context length exceeded: ", errorMessage);
  if (messages.length <= 2) throw new TokensExceededFirstMessageError();
  else throw new TokensExceededLaterMessageError();
}
if (errorCode === "insufficient_quota") {
  log.error("AI service provider billing quota exceeded!!!");
  throw new QuotaExceededError();
}
```

**Flow:** Two DIFFERENT wire signals mean "out of room": an explicit error code, OR a successful response whose finish_reason is `"length"` (model ran out mid-answer). Conversation stage picks the message: ≤2 messages (system+first user question) ⇒ "shorten your message or delete some columns"; later ⇒ adds "restart the conversation". Quota ⇒ day-scale backoff advice. Everything else non-200 becomes plain Error → retried → wrapped in RetryableError's fenced message.
**Invariant:** finish_reason=length MUST be treated as failure even on HTTP 200 — silently returning half a formula would corrupt the cell. The ≤2 boundary counts the SYSTEM prompt: a porter counting only user turns flips the two messages' applicability. QuotaExceeded extends NonRetryable (no retry can fix billing); RetryableError deliberately embeds the technical cause in a markdown code fence so users can report it.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "finish_reason === \"length\"" app/server/lib/OpenAIAssistantV1.ts && grep -n "messages.length <= 2" app/server/lib/OpenAIAssistantV1.ts && grep -n "class TokensExceededError\|class QuotaExceededError" app/server/lib/Assistant.ts'` → :221, :224, :109/:137.
Direct tests: `test/server/lib/OpenAIAssistantV1.ts` :229 quota (callCount===1), :292 finish-reason-length escalation, :312 restart-conversation message.

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"TokensExceededError QuotaExceeded NonRetryable context_length_exceeded","limit":5,"detail":"ids"}'
```

## Verdict
Adopt taxonomy + the 200-with-length-truncation trap verbatim; adapt wording; omit the First/Later split only if your UI has no conversation-stage concept.
