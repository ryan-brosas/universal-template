<!-- capsule-v2 -->
# Catalog-derived voice contract — how do you keep an enum-style option list, its TypeScript union, its runtime validator, and its default provably in sync from ONE literal?

**Source:** pi-better-openai MIT `main@1188f985389328cff660b6bdbe52f38fdb826c70`; Codebase Memory `pi-better-openai`. **Question:** A picker needs `{value,label}` options, config needs a validation guard, the session needs a typed default — how do all four surfaces derive from a single source of truth with zero drift?

## Voice catalog
**Path/Symbol:** `src/live/voices.ts` whole file (:1-21) — `LIVE_VOICE_OPTIONS` :1-11, `LIVE_VOICE_VALUES` :13, `LiveVoice` type :15, `DEFAULT_LIVE_VOICE` :17, `isLiveVoice` :19-21.
**Signature:** `isLiveVoice(value: unknown): value is LiveVoice`; `DEFAULT_LIVE_VOICE: LiveVoice = "sol"` (typed against the derived union).
**Data Shape:** Nine voices (`arbor breeze cove ember juniper maple sol spruce vale`) declared once as a `readonly` tuple via `as const`.

### Decisive source
```ts
export const LIVE_VOICE_OPTIONS = [
  { value: "arbor", label: "Arbor" },
  ...
  { value: "vale", label: "Vale" },
] as const;

export const LIVE_VOICE_VALUES = LIVE_VOICE_OPTIONS.map(({ value }) => value);
export type LiveVoice = (typeof LIVE_VOICE_OPTIONS)[number]["value"];
export const DEFAULT_LIVE_VOICE: LiveVoice = "sol";

export function isLiveVoice(value: unknown): value is LiveVoice {
  return typeof value === "string" && (LIVE_VOICE_VALUES as readonly string[]).includes(value);
}
```

**Flow:** one literal feeds four consumers — settings descriptor `values: LIVE_VOICE_VALUES` (config.ts:431) renders the picker; `readConfig`'s merge gate `if (isLiveVoice(parsed.live.voice)) config.live.voice = parsed.live.voice;` (config.ts:679) silently drops unknown values so the default applies; `DEFAULT_LIVE_CONFIG` seeds `voice: DEFAULT_LIVE_VOICE` (config.ts:171); the controller trims-then-falls-back `options.voice?.trim() || DEFAULT_LIVE_VOICE` (controller.ts:153). Adding a voice touches exactly one array.
**Invariant:** Type-level and runtime validity can never diverge because both derive from the same const tuple — the type is indexed off the literal, not hand-maintained; invalid persisted values are dropped at merge time (not thrown), making corrupt user configs self-healing to defaults; empty/whitespace voice strings fall back at construction, one layer later than invalid enums.
**Probe:** `tests/config.test.ts` (:175-191 "ignores invalid enum values while reading config" — `live.voice: "robot"` yields `parsed?.live` equal to `{enabled:false}`, voice key absent → default wins). Indirect passthrough: `tests/live-registration.test.ts` (:239 created session receives configured `voice: "vale"`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "LIVE_VOICE_OPTIONS isLiveVoice DEFAULT_LIVE_VOICE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt const-tuple catalog → derived values array + indexed union + typed default + narrowing guard. Adapt labels/catalog contents per host. Omit the specific voice names. Caveat: no dedicated voices.ts unit test exists — behavior is pinned indirectly through config-merge and registration tests above.
