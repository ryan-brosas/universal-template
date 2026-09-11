<!-- capsule-v2 -->
# Default-settings & default-instructions middlewares — how does the SDK inject defaults WITHOUT overriding user choices?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do you apply default call settings and a default system prompt at the middleware layer while preserving explicit user values, `0`/`null` sentinels, and middleware ordering?

## defaultSettingsMiddleware
**Path/Symbol:** `packages/ai/src/middleware/default-settings-middleware.ts:defaultSettingsMiddleware` (:15-33 whole).
**Signature:** `defaultSettingsMiddleware({ settings: Partial<CallOptions> }): LanguageModelMiddleware` — single `transformParams` hook.
**Data Shape:** `settings` is a partial of `{maxOutputTokens, temperature, stopSequences, topP, topK, presencePenalty, frequencyPenalty, responseFormat, seed, tools, toolChoice, headers, providerOptions}`.

### Decisive source
```ts
transformParams: async ({ params }) => {
  return mergeObjects(settings, params) as LanguageModelV4CallOptions;
},
```

**Flow:** `mergeObjects(defaults, userParams)` — argument ORDER is defaults-first, and merge-objects semantics (mined in pass 5's micro-utility capsule) make EXPLICIT user values win: `undefined` never overrides; arrays/Date/RegExp replace wholesale; prototype-dangerous keys (`__proto__`/`constructor`/`prototype`) are skipped before `hasOwnProperty` checks.
**Invariant:** (1) The temperature matrix pins merge-objects semantics exactly: user `temperature: 0` survives untouched (:157 'should keep 0 if settings.temperature is not set'); an `undefined` param falls to the default (:171 'should use default temperature if param temperature is undefined'); a `null` param BEATS a numeric default and stays `null` (:185 'should not use default temperature if param temperature is null' — nulls are never coerced to defaults); explicit values win outright (:199 'should use param temperature by default'). (2) Nested `providerOptions` DEEP-merge rather than replace (:47/:73/:114 tests), so provider-specific defaults compose with per-call extras. (3) The hook runs inside middleware `transformParams`, i.e., BEFORE `wrapGenerate/wrapStream` see params — stacking with other middlewares follows wrap order.
**Probe:** `bash -c "grep -n 'should not use default temperature if param temperature is null' $REFERENCE_ROOT/ai/packages/ai/src/middleware/default-settings-middleware.test.ts"` → `:185`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "defaultSettingsMiddleware transformParams mergeObjects", limit: 5 });
```

## defaultInstructionsMiddleware
**Path/Symbol:** `packages/ai/src/middleware/default-instructions-middleware.ts:defaultInstructionsMiddleware` (:16-44 whole).
**Signature:** `defaultInstructionsMiddleware({ instructions: Instructions | Instructions[] }): LanguageModelMiddleware`.
**Data Shape:** instructions normalized ONCE at closure creation into `LanguageModelV4Prompt` system messages preserving `providerOptions`.

### Decisive source
```ts
if (
  defaultSystemMessages.length === 0 ||
  params.prompt.some(message => message.role === 'system')
) {
  return params;                       // any system message ANYWHERE suppresses defaults
}
return { ...params, prompt: [...defaultSystemMessages, ...params.prompt] };
```

**Flow:** PREPEND-only: defaults go BEFORE existing messages, never merged into them; suppression is POSITION-INDEPENDENT — a system message ANYWHERE in the prompt (including one injected by an EARLIER middleware) disables the default entirely (:135/:230 tests).
**Invariant:** (1) "Has system" check scans the WHOLE prompt, not position 0 — checking only `prompt[0]` would double-inject after an earlier middleware appended a system message later. (2) Input params are never mutated (:200 'without mutating the input'); repeated calls re-evaluate fresh state but normalization happens once (:262 'apply defaults once on repeated calls'). (3) Empty instructions array = identity transform (:184). (4) `providerOptions` on each instruction message are preserved verbatim (:58).
**Probe:** `bash -c "grep -n 'should respect system messages added by an earlier middleware' $REFERENCE_ROOT/ai/packages/ai/src/middleware/default-instructions-middleware.test.ts"` → `:230`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "defaultInstructionsMiddleware transformParams prompt system", limit: 5 });
```

## Verdict
Adopt defaults-first deep-merge with null-means-unset, and whole-prompt system-message detection with prepend-only injection. Adapt the settings field list to your call-options surface. Omit providerOptions passthrough if your host lacks the concept (state the simplification).
