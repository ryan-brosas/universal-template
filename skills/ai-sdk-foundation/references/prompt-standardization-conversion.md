<!-- capsule-v2 -->
# Prompt standardization + wire conversion — how do user-facing prompt inputs become validated, tool-result-complete, provider-shaped messages?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What are the exact validation gates on prompt input, and what message surgery happens before anything reaches the provider?

## standardizePrompt
**Path/Symbol:** `packages/ai/src/prompt/standardize-prompt.ts:standardizePrompt` (:37-110).
**Signature:** `standardizePrompt({allowSystemInMessages? = false, system?, instructions? = system, prompt?, messages?}): Promise<{instructions: Instructions | undefined, messages: ModelMessage[]}>` — throws `InvalidPromptError` on every violation.
**Data Shape:** `instructions` defaults FROM `system`; accepts a string, a SystemModelMessage, or an array of them. `prompt` XOR `messages` (never both).

### Decisive source
```ts
if (prompt == null && messages == null) throw new InvalidPromptError({ message: 'prompt or messages must be defined' });
if (prompt != null && messages != null) throw new InvalidPromptError({ message: 'prompt and messages cannot be defined at the same time' });
// instructions must be string or all-system array:
if (typeof instructions !== 'string' && !asArray(instructions).every(m => m.role === 'system')) throw ...;
if (prompt != null && typeof prompt === 'string') messages = [{ role: 'user', content: prompt }];
else if (prompt != null && Array.isArray(prompt))  messages = prompt;
if (messages.length === 0) throw new InvalidPromptError({ message: 'messages must not be empty' });
if (!allowSystemInMessages && messages.some(m => m.role === 'system')) throw new InvalidPromptError({
  message: 'System messages are not allowed in the prompt or messages fields. Use the instructions option instead.' });
const validationResult = await safeValidateTypes({ value: messages, schema: z.array(modelMessageSchema) });
```

**Flow:** mutual-exclusion gate → instructions type check → prompt-to-messages normalization → emptiness gate → system-placement gate → schema validation → return.
**Invariant:** The system-in-messages ban is DEFAULT-ON (`allowSystemInMessages` opts in); even when allowed, a system message WITH PARTS still throws (test :96). Empty messages array is an error distinct from undefined. Validation runs against `modelMessageSchema` AFTER normalization, so errors quote the final shape.
**Probe:** `packages/ai/src/prompt/standardize-prompt.test.ts:6/:19` (system rejected by default), `:32/:64` (opt-in allows), `:96` (allowed-but-with-parts still throws), `:110` (empty array throws), `:174/:193` (system fallback / instructions precedence).

## convertToLanguageModelPrompt — combine, guard, filter
**Path/Symbol:** `packages/ai/src/prompt/convert-to-language-model-prompt.ts:convertToLanguageModelPrompt` (:38-191), `downloadAssets` (:442-542).
**Signature:** `convertToLanguageModelPrompt({prompt: StandardizedPrompt, supportedUrls, download? = createDefaultDownloadFunction(), provider?}): Promise<LanguageModelV4Prompt>`; throws `MissingToolResultsError`.
**Data Shape:** Pre-pass builds `approvalIdToToolCallId: Map` from assistant `tool-approval-request` parts, then collects `approvedToolCallIds: Set` from tool-message approval responses; `downloadedAssets: Record<url, {mediaType, data}>`.

### Decisive source
```ts
// combine consecutive tool messages into ONE tool message:
const lastCombinedMessage = combinedMessages.at(-1);
if (lastCombinedMessage?.role === 'tool') {
  // hoist the PREVIOUS message's providerOptions onto its LAST content part,
  // then the newer message's options replace the message-level value:
  lastCombinedMessage.content.push(...message.content);
  lastCombinedMessage.providerOptions = message.providerOptions;
}
// dangling-call guard: assistant tool-calls ADD ids, tool results DELETE them,
// approved calls are removed before EVERY check; non-tool roles trigger it:
for (const id of approvedToolCallIds) toolCallIds.delete(id);
if (toolCallIds.size > 0) throw new MissingToolResultsError({ toolCallIds: Array.from(toolCallIds) });
return combinedMessages.filter(message =>          // approval-response-only tool messages would
  message.role !== 'tool' || message.content.length > 0);   // ship as INVALID empty messages
```

**Flow:** parallel asset pre-download (URL file/image parts where the model lacks URL support per `supportedUrls` regex map; null results silently skipped) → instructions to leading system message(s) → per-message conversion → consecutive-tool merge → dangling-tool-call guard → empty-tool-message filter.
**Invariant:** The merge is ORDER-SENSITIVE: message-level providerOptions of the EARLIER message migrate onto its last part before being overwritten by the later message's — port both halves or options are silently lost. Approval responses remove ids from the missing set BEFORE each role check AND once more at the end; only genuinely dangling client-executed calls throw. Download planning covers user files AND tool-result `content` outputs in BOTH tool and assistant roles.
**Probe:** `packages/ai/src/prompt/convert-to-language-model-prompt.test.ts:1012` (two consecutive tool messages combine), `:292/:497` (unsupported URLs downloaded), `:543` (supported URLs pass through untouched), `:709/:763` (mediaType precedence over downloaded type); `convert-to-language-model-prompt.validation.test.ts:140` (dangling call ⇒ MissingToolResultsError), `:100` snapshot (provider-executed approval round-trip preserved).

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"standardizePrompt convertToLanguageModelPrompt MissingToolResultsError","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the five-gate standardization order, consecutive-tool merging with providerOptions migration, and the approved-aware dangling guard verbatim; adapt the URL-support policy table to your provider matrix; omit legacy v8-era output mapping. These two functions are the entry boundary every orchestrator capsule already assumes.
