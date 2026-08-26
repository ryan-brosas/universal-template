<!-- capsule-v2 -->
# Decision parsing fail-safe — what happens when the supervisor LLM returns garbage?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** Which failure of a supervisor response must degrade to "continue", and which must degrade to "steer"?

## parseDecision + safeContinue (`src/session/response-parser.ts`)
**Path/Symbol:** `src/session/response-parser.ts:parseDecision` (:11-32), `safeContinue` (:35-37).
**Signature:** `parseDecision(text: string): SteeringDecision`; `safeContinue(reason): {action:'continue', reasoning, confidence:0}`.
**Data Shape:** `SteeringDecision = {action:'continue'|'steer'|'done', message?, reasoning, confidence, asi?}`.

### Decisive source
```ts
const jsonMatch = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/)   // 1st: fenced block
               ?? text.match(/(\{[\s\S]*\})/);                    // 2nd: first {...} span
const jsonStr = jsonMatch?.[1] ?? text.trim();                    // 3rd: raw text as JSON
try {
  const parsed = JSON.parse(jsonStr);
  const action = parsed.action;
  if (action !== 'continue' && action !== 'steer' && action !== 'done')
    return safeContinue('Invalid action in supervisor response'); // enum mismatch ⇒ continue
  return {
    action,
    message: typeof parsed.message === 'string' ? parsed.message.trim() : undefined,
    reasoning: typeof parsed.reasoning === 'string' ? parsed.reasoning : '',
    confidence: typeof parsed.confidence === 'number' ? parsed.confidence : 0.5, // DEFAULT 0.5
    asi: parsed.asi && typeof parsed.asi === 'object' ? parsed.asi : undefined,
  };
} catch { return safeContinue('Failed to parse supervisor JSON decision'); }
```

**Flow:** fenced JSON → bare object → raw-text triple fallback; ANY parse/enum failure yields `{continue, confidence:0}` so a broken supervisor NEVER kills or hijacks the agent run. Field-level defaults: missing confidence = 0.5 (neutral), missing reasoning = '', missing message = undefined (a steer without message is filtered at call sites).
**Invariant:** (1) All parse failures are CONTINUE — the dangerous action is omission, not commission, because continue just waits for the next checkpoint while a bogus steer/done would end supervision wrongly. (2) Confidence default 0.5 matters: mid-run steering requires ≥0.85, so an omitted confidence silently disables mid-run steers — deliberate conservatism. (3) The regexes are ordered: fence extraction wins over brace-span because prose may contain braces.
**Probe:** `tests/parsing.test.ts` — `extracts JSON from markdown code block` (:48), `extracts JSON from curly braces when no code block` (:74), `returns continue on invalid JSON` (:83), `returns continue on invalid action` (:92), `handles missing fields with defaults` (:104).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "parseDecision safeContinue confidence default", limit: 8 });
```

## Verdict
Adopt the three-stage extraction + all-failures-continue + per-field defaults exactly. Adapt action enum if your loop has more verbs (keep continue as the ONLY failure value). Omit nothing else — this is fully portable.
