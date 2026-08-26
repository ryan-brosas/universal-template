<!-- capsule-v2 -->
# Token-exceeded model escalation ladder — how does an assistant survive context-length failures without hammering the provider?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** In what order does OpenAIAssistantV1 try default model → longer-context model → shorter prompt, and which errors abort immediately?

## _getCompletion: three escalating attempts; TokensExceeded* are NonRetryable inside _fetchCompletionWithRetries
**Path/Symbol:** `app/server/lib/OpenAIAssistantV1.ts`: `_fetchCompletionWithRetries` (:242–268, maxAttempts=3 :250, NonRetryable rethrow :255–257), `_getCompletion` (:270–318) — default try :280–289, longer-model :293–304, short-prompt rebuild :306–317 (`includeAllTables:false, includeLookups:false` :308–309).
**Signature:** `_getCompletion(messages, {generatePrompt, user}): Promise<string>`.
**Data Shape:** Escalation state lives in the REQUEST SHAPE itself (message list rebuilt), not in retries counters.

### Decisive source
```ts
try { return await this._fetchCompletionWithRetries(messages, { user, model: this._model }); }
catch (e) { if (!(e instanceof TokensExceededError)) throw e; }

if (this._longerContextModel) {
  try { return await this._fetchCompletionWithRetries(messages, { user, model: this._longerContextModel }); }
  catch (e) { if (!(e instanceof TokensExceededError)) throw e; }
}
// If we (still) hit the token limit, try a SHORTER schema prompt as a last resort.
const prompt = await generatePrompt({ includeAllTables: false, includeLookups: false });
return await this._fetchCompletionWithRetries(
  [prompt, ...messages.slice(1)],     // replace message[0] (the big schema prompt)
  { user, model: this._longerContextModel || this._model },
);
```

**Flow:** transient failures (network/5xx) retry in-place up to 3 with 1s delay then surface as user-facing RetryableError. Context-limit failures DON'T retry the same shape: escalate to the configured longer-context model, then shrink the PROMPT (drop other tables' schemas and lookup docs from the system message) while keeping conversation history (`slice(1)` preserves everything after the system prompt).
**Invariant:** Error taxonomy drives control flow: `NonRetryableError` subclasses (TokensExceeded*, QuotaExceeded) escape the retry loop instantly; only generic errors consume attempts. Prompt-shortening replaces index 0 specifically because that slot IS the schema prompt — a porter trimming from the tail would delete the USER'S question instead. If even the short prompt overflows, the TokensExceeded propagates to a tailored user message.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && sed -n "270,290p" app/server/lib/OpenAIAssistantV1.ts | grep -n "TokensExceededError\|this._model" && grep -n "includeAllTables: false" app/server/lib/OpenAIAssistantV1.ts'` → catch gates at relative :5-8/:16-18 and :308.
Direct tests: `test/server/lib/OpenAIAssistantV1.ts` :244 "switches to a longer model…", :262 "switches to a shorter prompt…" (asserts Table2 absent + lengthOf(systemMessageContent, 1001)).

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"_getCompletion longerContextModel generatePrompt schema prompt retry","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the taxonomy-gated escalation order verbatim; adapt model names/prompt builder to your host; omit the longer-model rung when unset (the code already degrades gracefully).
