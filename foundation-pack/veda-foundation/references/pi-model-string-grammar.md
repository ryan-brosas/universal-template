<!-- capsule-v2 -->
# Pi model-string grammar — how do you split `pi/<provider>/<model…>` when the model itself contains slashes?

**Source:** veda-ts MIT `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6` (v0.75.9); Codebase Memory `veda`. **Question:** Where is the ONE permitted split point in a pi routing string, and what must the parser do with legacy prefixes and multi-slash provider paths?

## First-slash parse with strict prefix gate
**Path/Symbol:** `src/backend/pi.ts` : `parsePiModel` (:5-17); sibling helper `toPiThinking` (:19-32) maps all six reasoning levels 1:1 (minimal/low/medium/high/xhigh/max — identity, NOT downgraded like the claude backend).
**Signature:** `function parsePiModel(model: string): { provider: string; model: string }`.
**Data Shape:** input MUST start `pi/`; output `{provider, model}` where model retains ALL remaining slashes; throws on any violation.

### Decisive source
```ts
export function parsePiModel(model: string): { provider: string; model: string } {
  if (!model.startsWith('pi/')) {
    throw new Error(`Model string must start with pi/: ${model}`);
  }
  const rest = model.slice('pi/'.length);
  const firstSlash = rest.indexOf('/');
  if (firstSlash === -1) {
    throw new Error(`Model string must start with pi/ and contain provider/model: ${model}`);
  }
  const provider = rest.slice(0, firstSlash);
  const modelName = rest.slice(firstSlash + 1);
  return { provider, model: modelName };
}
```

**Flow:** prefix gate (`pi/`, else throw) → FIRST slash after prefix = single split point → everything left = provider, everything right (slashes intact) = model. `'pi/fireworks/accounts/fireworks/routers/kimi-k2p6'` → `{provider:'fireworks', model:'accounts/fireworks/routers/kimi-k2p6'}`.
**Invariant:** exactly one split at the first slash — never split further, never rsplit; bare `pi` and empty string throw; legacy `mu/` prefix intentionally rejected with the same "must start with" error so old configs fail LOUDLY instead of silently routing nowhere. The provider becomes a CLI `--provider <provider>` flag value and model a `--model <model>` flag value (see run()).
**Probe:** `tests/backend/pi.test.ts:4-42` — seven pins incl. multi-slash passthrough and the `mu/wafer/GLM-5.1` legacy rejection. Run: `bun test tests/backend/pi.test.ts`.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"veda","query":"parsePiModel provider model","limit":5,"detail":"ids"}'
```
→ resolves `veda.src.backend.pi.parsePiModel Function src/backend/pi.ts 5-17`.

## Verdict
Adopt the grammar (prefix-gate → first-slash-split → slashes-passthrough → loud legacy rejection) verbatim. Adapt error message wording. Omit nothing — this is small enough to port whole. Direct-test coverage strong (7 tests).
