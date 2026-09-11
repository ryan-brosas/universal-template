<!-- capsule-v2 -->
# Safe-continue decision contract — fence-tolerant decision parsing where every failure returns, none throw

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How should an LLM's JSON verdict be parsed so that malformed output degrades instead of crashing the supervisor?

## Extraction ladder + field validation
**Path/Symbol:** `src/session/response-parser.ts:11-32` (`parseDecision`), `safeContinue` :35-37.
**Signature:** `parseDecision(text: string): SteeringDecision`; `safeContinue(reason: string): SteeringDecision`.
**Data Shape:** Extraction ladder: fenced ```json block → any fenced block → first `{...}` span → raw trimmed text. Valid actions: exactly `continue|steer|done`. Defaults: missing reasoning `''`, confidence `0.5`, asi only when object.

### Decisive source
```ts
export function parseDecision(text: string): SteeringDecision {
  const jsonMatch = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/) ?? text.match(/(\{[\s\S]*\})/);
  const jsonStr = jsonMatch?.[1] ?? text.trim();
  try {
    const parsed = JSON.parse(jsonStr) as Partial<SteeringDecision>;
    const action = parsed.action;
    if (action !== 'continue' && action !== 'steer' && action !== 'done') {
      return safeContinue('Invalid action in supervisor response');
    }
    return {
      action,
      message: typeof parsed.message === 'string' ? parsed.message.trim() : undefined,
      ...
    };
  } catch { return safeContinue('Failed to parse supervisor JSON decision'); }
}
```

**Flow:** model text → extract candidate JSON (tolerating markdown fences the system prompt forbade) → parse → validate action enum → coerce fields individually → any failure ⇒ typed continue with the reason embedded.
**Invariant:** The failure reason travels INSIDE the decision (`reasoning` field) so upstream logging shows WHY a continue happened. Field coercion is per-field (`typeof x === 'string' ? … : default`) — one bad field never poisons the rest. `steer` without message is still returned; callers enforce their own message+confidence gates.
**Probe:** `grep -c safeContinue src/session/client.ts src/session/response-parser.ts` → 3 + 3 lines (uses + definition); `grep -cn "action !== .continue. && action !== .steer. && action !== .done." src/session/response-parser.ts` → 1. Direct tests: `tests/parsing.test.ts:48/:62/:74/:83/:92/:104/:116` ("extracts JSON from markdown code block", "…plain code block", "…curly braces when no code block", "returns continue on invalid JSON", "on invalid action", "handles missing fields with defaults", "trims message whitespace").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "parseDecision JSON fence markdown safeContinue", limit: 10 });
```

## Verdict
Adopt the whole contract: ladder, enum gate, per-field defaults, reason-carrying typed failures. Adapt the action enum to your decision space. Omit the curly-brace fallback only if you control the model output format end-to-end — against real models, fences appear despite instructions.
