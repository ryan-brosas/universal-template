<!-- capsule-v2 -->
# Moderation funnel — how is user-generated text gated from regex to AI to verdict?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** What checks run, in what order, and when does a "flagged" verdict still let content through?

## moderateContent layered ladder
**Path/Symbol:** `apps/web/src/features/moderation/mutations.ts:moderateContent` (lines 104–195) + `moderateContentWithAI` (23–73); call sites `apps/web/src/trpc/routers/polls.ts:make` (129–159).
**Signature:** `moderateContent({ userId, userEmail, content: Record<string,string>, trusted = false }): Promise<ModerationResult>` where ModerationResult = `{verdict: "safe"|"flagged"|"error", reason}`.
**Data Shape:** env gates MODERATION_ENABLED==="true" + OPENAI_API_KEY; BANNED_DOMAINS CSV; AI timeout 30s; model gpt-4.1.

### Decisive source
```ts
if (containsBannedDomain(textToModerate)) {
  after(() => banUser({ userId, reason: "Automatic ban: banned domain detected in content" }));
  return { verdict: "flagged", reason: "Content contains a banned domain" };
}
const hasSuspiciousPatterns = containsSuspiciousPatterns(textToModerate);
if (hasSuspiciousPatterns) {
  const result = await moderateContentWithAI(textToModerate);
  if (result.verdict === "flagged") {
    /* ... support-email audit trail via after() ... */
    if (trusted) {
      logger.info({ userId }, "Content flagged but user is trusted, allowing through");
      return safeResult;
    }
  }
  return result;
}
return safeResult;
```
```ts
} catch (err) {
  aiLogger.error({ error: err }, "AI moderation failed");
  return { verdict: "safe", reason: "AI moderation failed, defaulting to safe" };
}
```

**Flow:** env-off → safe; banned domain → flag + auto-ban (async); suspicious-pattern hit → AI check; AI flagged + NOT trusted (pro tier or self-host bypasses) → router returns structured `{ok:false, error:{code:"INAPPROPRIATE_CONTENT"}}` instead of throwing — the client shows a toast, not an error boundary. Every failure mode defaults to SAFE (fail-open): missing key, AI timeout, thrown error.
**Invariant:** the funnel is cheap-first (regex) expensive-later (LLM), fail-open everywhere except the deterministic banned-domain rule; `trusted` (pro space) overrides AI flags but NOT the banned-domain ban. Verdict travels as data, not as an exception, so callers can render UX around it.
**Probe:** deterministic grep anchors: `grep -n 'defaulting to safe' apps/web/src/features/moderation/mutations.ts` → line 70; `grep -cF 'INAPPROPRIATE_CONTENT' apps/web/src/trpc/routers/polls.ts` → 2.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "moderateContent flagged trusted", limit: 5 });
```

## Verdict
Adopt the ordering and fail-open policy verbatim; adapt the pattern list + LLM prompt/model; omit PostHog flag events. No direct unit test for the funnel — prompt and order are comment-pinned source only.
