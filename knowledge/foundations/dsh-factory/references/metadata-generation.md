<!-- capsule-v2 -->
# Metadata generation — how do AI-generated titles stay bounded, honest, and reversible?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How do I generate task titles/descriptions with an auxiliary model while guaranteeing deterministic fallbacks, exact request receipts, and never clobbering user text?

## fallback / factoryMetadataRequest / generateFactoryMetadata
**Path/Symbol:** `packages/domain/src/metadata.ts` (:31–131) + `packages/domain/src/index.ts` (`completeMetadataGeneration`) (:1146–1188).
**Signature:** `boundFactoryMetadataText(value, maxBytes): string`; `fallbackFactoryMetadata(prompt, limits)`; `generateFactoryMetadata(ctx, request, limits): Promise<FactoryGeneratedMetadata>`.
**Data Shape:** strict-JSON contract `{title, description}` only; limits default maxInput 16_000B, maxTitle 160B, maxDescription 800B, timeout 30s, maxTokens 160; durable receipt `FactoryMetadataGeneration{status: running|succeeded|failed, route, system, input, output?, error?}` retained to a 500-entry cap.

### Decisive source
```ts
export function boundFactoryMetadataText(value: string, maxBytes: string): string // (actual: maxBytes: number)
const normalized = value.replaceAll(/\s+/gu, ' ').trim()
let result = ''
for (const character of normalized) {
    if (Buffer.byteLength(result + character, 'utf8') > maxBytes) break   // UTF-8 code-point safe
    result += character
}
...
if (options.replaceTitle && task.title === fallback.title) task.title = generated.title
```

**Flow:** createTask/intake commit the task IMMEDIATELY with deterministic fallback metadata (first sentence = title) and append a `running` generation receipt → AFTER commit, generate through the shared LLM runtime (frozen options, `purpose: 'session-title'`, AbortSignal.timeout, finish-reason error mapping incl. tool-calls rejection) → second commit marks the receipt succeeded/failed and REPLACES title/description ONLY where the user didn't supply one AND the field still equals the fallback value.
**Invariant:** The fallback-equality guard makes generated metadata non-destructive — user-authored or already-changed fields are never overwritten by the async model response; byte budgets are enforced per UTF-8 character so truncation can't split code points; failures are bounded text stored ON the receipt, never thrown at the caller's original mutation.
**Probe:** `packages/domain/tests/domain.spec.ts` "keeps deterministic metadata and logs a bounded failure when generation is invalid" + "logs custom workspace metadata prompts through the configured title model". Deterministic from repo root: `grep -c "purpose: 'session-title'" packages/domain/src/metadata.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "generateFactoryMetadata", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified via sibling name-pattern queries on this project.)

## Verdict
Adopt commit-first/fallback-now/generate-later with the equality-guard overwrite. Adapt LLM runtime calls. Omit Typert route resolution internals.
