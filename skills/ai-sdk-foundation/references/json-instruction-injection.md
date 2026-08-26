<!-- capsule-v2 -->
# JSON instruction injection — how do you force JSON output from providers whose wire format has no native responseFormat, without corrupting an existing system message?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** When a provider ignores structured-output APIs, where exactly do the schema and the "answer in JSON" demand go — and what must a porter preserve so the injected prompt stays stable across calls?

## Prompt-string injector (core) + message twin
**Path/Symbol:** `packages/provider-utils/src/inject-json-instruction.ts:injectJsonInstruction` (:12–34); message-level twin `injectJsonInstructionIntoMessages` (:36–63). Legacy per-call copy: `packages/ai/src/generate-object/inject-json-instruction.ts` (:8–30, identical body).
**Signature:** `function injectJsonInstruction({prompt?, schema?, schemaPrefix?, schemaSuffix?}): string`.
**Data Shape:** Defaults are CONDITIONAL on schema presence: prefix `'JSON schema:'` only when schema != null; suffix `'You MUST answer with a JSON object that matches the JSON schema above.'` when schema present, else generic `'You MUST answer with JSON.'`. Empty-string prompt (`''`) is treated as ABSENT via `prompt.length > 0` guards.

### Decisive source
```ts
return [
  prompt != null && prompt.length > 0 ? prompt : undefined,
  prompt != null && prompt.length > 0 ? '' : undefined, // add a newline if prompt is not null
  schemaPrefix,
  schema != null ? JSON.stringify(schema) : undefined,
  schemaSuffix,
]
  .filter(line => line != null)
  .join('\n');

// message twin: copies (never mutates caller's) first system message,
// synthesizes one if absent, preserves all non-system messages:
const systemMessage = messages[0]?.role === 'system'
  ? { ...messages[0] } : { role: 'system', content: '' };
systemMessage.content = injectJsonInstruction({prompt: systemMessage.content, ...});
return [systemMessage, ...(messages[0]?.role === 'system' ? messages.slice(1) : messages)];
```

**Flow:** provider adapters lacking native responseFormat call the message twin inside their `doGenerate/doStream` (e.g. mistral-chat-language-model.ts:154 replaces the outgoing prompt; amazon-bedrock-chat-language-model.ts:432 filters the prompt first) → schema JSON.stringify'd verbatim between prefix/suffix lines → appended to (or creating) the SYSTEM slot only.
**Invariant:** Injection targets the FIRST system message and never duplicates it or touches other roles; the exact line layout with conditional defaults is what tests pin — reordering or unconditional prefixes changes prompts for every schema-less call. The schema goes through plain `JSON.stringify`, so hosts caching prompts must keep schema conversion key-order deterministic (cross-ref flexible-schemas.md).
**Probe:** `packages/provider-utils/src/inject-json-instruction.test.ts` :18 basic join; :38 only-schema ('JSON schema:' + schema + MUST-match suffix); :49 neither → bare `'You MUST answer with JSON.'`; :54 custom overrides replace BOTH defaults; :69 empty-string prompt == absent; :126 special characters survive.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "injectJsonInstructionIntoMessages json instruction schema prompt", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the conditional-defaults join and the copy-first-system-message rule verbatim; adapt default wordings/prefixes to host voice; omit the legacy duplicate in packages/ai (use the provider-utils export — the packages/ai copy exists only for the deprecated streamObject/generateObject seam). Coverage caveat: index best-effort; excerpts read directly at HEAD.
