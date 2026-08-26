<!-- capsule-v2 -->
# Live wire codec — how do you parse a realtime server's events without letting malformed frames crash or lie about their shape?

**Source:** pi-better-openai MIT `main@86814e9047996abba08e4c907e23286329196fe0`; Codebase Memory `pi-better-openai`. **Question:** How should a WebSocket client parse unknown JSON payloads into a closed event union so every handler can trust the shape?

## Wire-protocol parser
**Path/Symbol:** `src/live/protocol.ts:parseLiveServerEvent` (:144-166), helpers :50-142.
**Signature:** `parseLiveServerEvent(payload: unknown): LiveServerEvent | null`.
**Data Shape:** Input is a raw string OR already-parsed object; output is a discriminated union (`LiveServerEvent`) or `null` = frame not usable. Every variant carries only narrowed primitive fields.

### Decisive source
```ts
export function parseLiveServerEvent(payload: unknown): LiveServerEvent | null {
  const parsed = parsePayload(payload);
  if (!parsed || typeof parsed.type !== "string") return null;
  switch (parsed.type) {
    case "session.started":
    case "session.updated":
      return parseSessionEvent(parsed.type, parsed);
    // ... one branch per known wireType ...
    default:
      return { type: "unknown", wireType: parsed.type };
  }
}
```
Key helper discipline (:52-66): `parsePayload` accepts string-or-object ("double encoding" tolerance), returns `null` on JSON.parse failure AND on arrays/non-objects (`isRecord` excludes `Array.isArray`). Per-type validators (:68-142) return `null` per-field-failure instead of throwing, and `parseDelegationCreatedEvent` FILTERS content items item-by-item rather than rejecting the whole event (:107-117). Error extraction ladders `payload.message` → `payload.error.message` → `JSON.stringify(error)` → `String(value)` (:134-142).

**Flow:** raw frame → parsePayload (string→JSON→record gate) → switch on `type` → per-type validator narrows fields → typed event, or `{type:"unknown",wireType}` catch-all, or `null` silent-drop.
**Invariant:** The parser NEVER throws and NEVER passes an unvalidated object to consumers; unknown wire types become data (`unknown` variant), not exceptions — handlers switch exhaustively and stay total.
**Probe:** `tests/live-protocol.test.ts` (:16 string payload parsed, :47 input_transcript, :58 output_audio.delta base64, :62 nested error.message).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "parseLiveServerEvent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the never-throw closed-union parser with per-field validators and an explicit `unknown` wire type — this is the reusable contract. Adapt the specific event names/wireTypes to your protocol. Omit the Codex-specific session/delegation semantics.
