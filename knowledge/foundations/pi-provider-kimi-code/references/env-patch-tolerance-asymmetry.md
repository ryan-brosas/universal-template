<!-- capsule-v2 -->
# Env patch tolerance asymmetry — which environment-variable mistakes are fatal and which are silently ignored?

**Source:** pi-provider-kimi-code MIT `main@794330400343d6f0cd0059635187b233c4d90273`; Codebase Memory `pi-provider-kimi-code`. **Question:** When env vars feed a validated config tree, do you reject bad values at parse time or let validation catch them — and does the answer differ by value type?

## Env patch tolerance asymmetry
**Path/Symbol:** `src/config.ts:227-276` (`envConfigPatch`); parsers `parsePositiveNumber` :278-282, `parseFiniteNumber` :284-288; consumed as the `"env"` layer in `loadLayers` :501-504.
**Signature:** `envConfigPatch(env: NodeJS.ProcessEnv): KimiCodeConfigPatch`; both parsers are `(value: string | undefined) => number | undefined`.
**Data Shape:** recognized vars: `KIMI_MODEL_MAX_CONTEXT_SIZE`, `KIMI_MODEL_TEMPERATURE`, `KIMI_MODEL_TOP_P`, `KIMI_MODEL_MAX_COMPLETION_TOKENS`, `KIMI_MODEL_THINKING_KEEP`, `KIMI_CODE_UPLOAD_THRESHOLD_BYTES`, `KIMI_CODE_PROTOCOL`, `KIMI_MODEL_CAPABILITIES` (CSV).

### Decisive source
```ts
function parsePositiveNumber(value: string | undefined): number | undefined {
  if (!value) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}
```
```ts
const thinkingKeep = env.KIMI_MODEL_THINKING_KEEP?.trim();
if (temp !== undefined || topP !== undefined || maxCompletionTokens !== undefined || thinkingKeep) {
  patch.model = {
    ...patch.model,
    ...(thinkingKeep ? { thinkingKeep } : {}),
    generation: {
      ...(temp !== undefined ? { temperature: temp } : {}),
      ...
    },
  };
}
const protocol = env.KIMI_CODE_PROTOCOL?.trim();
if (protocol) patch.protocol = protocol;
```
```ts
const caps = new Set(capabilities.split(",").map((cap) => cap.trim().toLowerCase()).filter(Boolean));
patch.model = {
  ...patch.model,
  reasoning: caps.has("thinking") || caps.has("always_thinking"),
  input: caps.has("image_in") ? ["text", "image"] : ["text"],
};
```

**Flow:** the asymmetry — numeric vars go through the tolerant parsers, so
`KIMI_MODEL_TEMPERATURE=banana` yields `undefined` and is OMITTED from the patch (the
lower layer's value survives; nothing tells the user). String passthroughs
(`thinkingKeep`, `protocol`) are only trimmed and flow raw into the merged patch, so an
invalid value like `KIMI_MODEL_THINKING_KEEP=banana` survives the merge and detonates at
load-time validation as `ConfigError "<kimi-code-config>/model/thinkingKeep: expected …"`.
The capabilities CSV is a projection, not a parse: unknown capability tokens are ignored;
presence of `image_in` REPLACES the input array wholesale (a lower layer can't add video
back); any capability present forces reasoning/input decisions even if only unrelated
tokens were listed. The whole generation object is emitted whenever ANY of its four vars
is set, with per-key spreads omitting unset ones.
**Invariant:** silent-drop applies only to values that fail their parser; anything that
parses to a plausible raw string is deferred to the loud validator. Empty/whitespace env
values behave as unset (`if (!value)` / truthiness guards).

**Probe:** `tests/config.test.ts:126-151` — all six numeric/string vars map through
(expecting generation `{temperature:0.2, topP:0.8, maxCompletionTokens:12345}`,
thinkingKeep "last", threshold 4096). The failure side is pinned indirectly:
config.test.ts:153-164 proves string garbage reaching validation throws. Executed GREEN
this pass (config suite 12/12).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-provider-kimi-code", query: "envConfigPatch KIMI_MODEL environment variables parse number", limit: 5 });
// observed: parsePositiveNumber #1 (-21.16), parseFiniteNumber #2, envConfigPatch #3
```

## Verdict
Adopt typed parsing at the env boundary with a deliberate per-type tolerance policy —
numbers forgiving (drop + inherit), enums unforgiving (defer to loud validation). Adapt
the var vocabulary and capability token set to your host. Omit the CSV-capabilities
projection unless you need one variable to flip multiple capability fields.
