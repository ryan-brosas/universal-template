<!-- capsule-v2 -->
# Pointer validation projection — how do you fail loudly on bad user config AND silently drop unknown keys in the same pass?

**Source:** pi-provider-kimi-code MIT `main@794330400343d6f0cd0059635187b233c4d90273`; Codebase Memory `pi-provider-kimi-code`. **Question:** What should a config validator do with a typo'd field, a wrong-typed value, or a null generation number — and what exactly does the error tell the user?

## Pointer validation projection
**Path/Symbol:** `src/config.ts:421-438` (`validateKimiCodeConfig`); error type `ConfigError` :93-103; throw helper `fail` :290-292; guard family `requireRecord` :294-301, `requirePositiveNumber` :303-306, `requireBoolean` :308-311, `requireProtocol` :313-320, `requireInputArray` :322-336, `requireReasoningMap` :338-353, `requireThinkingKeep` :355-366, `requireGeneration` :368-381; sub-validators `validateModelConfig` :383-398, `validateToolsConfig` :400-419.
**Signature:** guards are `(raw: unknown, configPath: string, pointer: string): T` — every failure throws `never` via `fail(configPath, pointer, message)`.
**Data Shape:** `ConfigError` carries `configPath` (file or `"<kimi-code-config>"`) plus an optional JSON-pointer-style `pointer` ("/model/maxTokens"); the composed message is `` `${configPath}${pointer}: ${message}` ``.

### Decisive source
```ts
export class ConfigError extends Error {
  public readonly configPath: string;
  public readonly pointer?: string;

  constructor(message: string, configPath: string, pointer?: string) {
    super(pointer ? `${configPath}${pointer}: ${message}` : `${configPath}: ${message}`);
    this.name = "ConfigError";
    this.configPath = configPath;
    this.pointer = pointer;
  }
}
```
```ts
function requireGeneration(raw: unknown, configPath: string, pointer: string): ModelGeneration {
  const record = requireRecord(raw, configPath, pointer);
  const result: ModelGeneration = {};
  const knownKeys = ["temperature", "topP", "maxCompletionTokens"] as const;
  for (const key of knownKeys) {
    const value = record[key];
    if (value === undefined || value === null) continue;
    if (typeof value !== "number" || !Number.isFinite(value)) {
      fail(configPath, `${pointer}/${key}`, `expected a number, got ${JSON.stringify(value)}`);
    }
    result[key] = value;
  }
  return result;
}
```

**Flow:** validateKimiCodeConfig never annotates the input — it BUILDS a new object from
the leaves each guard returns. Three consequences: (1) unknown keys anywhere in the tree
are silently dropped (typo `maxToken:` vanishes rather than erroring); (2) known keys with
wrong types throw immediately with the offending file + pointer + JSON-stringified value
(`expected a positive number, got "32000"` — note strings are not coerced); (3) `null`
generation values are skipped while wrong-typed ones throw. `validateKimiCodeConfig(raw,
configPath = "<kimi-code-config>")` accepts a path argument so save-time re-validation can
attribute errors to the real file (saveKimiCodeConfigFile :565-568 passes it).
**Invariant:** load-time validation runs against the MERGED blob with the placeholder path
`"<kimi-code-config>"` because no single file owns a merged bad value; only single-file
write paths re-validate with the concrete path. Guards are total functions of `unknown` —
no cast-and-hope anywhere in the family.

**Probe:** `tests/config.test.ts:153-164` — project file with `model.maxTokens:"32000"`
(string) throws ConfigError whose `.pointer === "/model/maxTokens"`; :181-189 —
`generation:{temperature:null}` validates to `{}`; :191-195 — all three tool names survive
projection. Executed GREEN this pass (config suite 12/12).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-provider-kimi-code", query: "validateKimiCodeConfig requireReasoningMap requireThinkingKeep validateModelConfig", limit: 6 });
// observed: 4/4 guard-family symbols (total=4), requireReasoningMap #1 … validateKimiCodeConfig #4
```

## Verdict
Adopt guard-per-leaf with (path, pointer, message) errors — it is the cheapest way to make
hand-edited JSON debuggable without a schema dependency. Adapt: decide explicitly whether
typos should error (here they don't — projection is silent) and whether to coerce numeric
strings (here they refuse). Omit the null-skip special case if your wire format rejects
nulls upstream anyway.
