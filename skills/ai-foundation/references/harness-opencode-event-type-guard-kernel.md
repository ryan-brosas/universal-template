<!-- capsule-v2 -->
# OpenCode event type-guard kernel — how do you parse a third-party event stream whose fields you cannot trust to exist?

**Source:** Vercel AI SDK (inspo/ai) Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory project `ai` (MCP not connected this session — direct source read fallback). **Question:** what is the minimal shared primitive that lets every event consumer narrow `unknown` wire data without a schema engine?

## asOpenCodeObject + structural types
**Path/Symbol:** `packages/harness-opencode/src/bridge/opencode-types.ts` (33L whole): `asOpenCodeObject` :29, `OpenCodeObject` :1, `OpenCodeMessageInfo` :3, `OpenCodeEventProperties` :12, `OpenCodeEvent` :23. Consumers: `opencode-events.ts` :73/:76/:105/:286/:292/:304/:313, `create-emit-stream-event.ts` :529–581, `opencode-usage.ts` :43/:108–133, `opencode-finish-step.ts` :29, `bridge/index.ts` :202/:208/:617/:991/:1427/:1431/:1447.

### Decisive source
```ts
export type OpenCodeMessageInfo = {
  id?: unknown;
  role?: unknown;
  type?: unknown;
  providerID?: unknown;
  modelID?: unknown;
  tokens?: unknown;
};

export type OpenCodeEventProperties = OpenCodeObject & {
  info?: OpenCodeMessageInfo;
  provider?: { metadata?: unknown };
  source?: { callID?: unknown };
  status?: { type?: unknown; attempt?: unknown; message?: unknown };
};

export function asOpenCodeObject(value: unknown): OpenCodeObject | undefined {
  return value != null && typeof value === 'object' && !Array.isArray(value)
    ? (value as OpenCodeObject)
    : undefined;
}
```

**Data Shape:** the guard accepts only non-null, non-array objects and returns `undefined` otherwise — every field in the companion types is optional and typed `unknown`, so narrowing is the CONSUMER's job per access site; the types describe the wire's SHAPE without asserting any field's type.

**Flow:** raw wire value → `asOpenCodeObject` narrows to a record (or `undefined`) → consumer chains further guards on the result (`asOpenCodeObject(part.state)`, `asOpenCodeObject(record?.cache)`, …) → each consumer site decides what a missing field means (skip, default, degrade) — the kernel never throws, never defaults, never logs.

**Invariant:** the guard must reject arrays (an array is `typeof 'object'` but is not a record) and `null`; it must never throw; all type assertions stay within the guard's proven bounds. This is the primitive the pass-26 event-envelope capsule's normalization ladder is built on — that capsule owns the event semantics; this one owns the guard itself.

**Probe:** `packages/harness-opencode/src/bridge/opencode-events.test.ts` (10 cases over the normalization ladder that consumes this guard) and `opencode-usage.test.ts` (3+3 cases) — the guard is exercised at every consumer site; no dedicated opencode-types.test.ts exists (the kernel is 6 lines; its behavior is pinned through consumers).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "asOpenCodeObject unknown event narrowing", limit: 10, fields: ["signature", "name", "file"] });
```
Expected rank: opencode-types.ts, then the five consumer files.

## Verdict
Adopt the non-array-object guard + all-unknown-optional-types pair for any untrusted wire surface; adapt the type names to your domain; omit the per-event property shapes (OpenCode-specific). Coverage caveat: no dedicated unit file for the 6-line kernel — behavior is pinned through the consumer test suites listed above.
