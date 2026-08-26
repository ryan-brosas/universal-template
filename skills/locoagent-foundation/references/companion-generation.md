<!-- capsule-v2 -->
# Deterministic companion generation & sprite rendering — how do you give every user a stable "randomized" character without storing (or letting them fake) its properties?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you derive a collectible's rarity/species/stats purely from a user ID so it survives storage loss and config tampering, and how do layered ASCII sprites stay height-stable across animation frames?

## Bones/soul split: derived parts vs stored parts
**Path/Symbol:** `src/buddy/companion.ts`:`roll`, `getCompanion`, `rollFrom` (`:84-133`); `src/buddy/types.ts`:`CompanionBones`, `StoredCompanion`, `RARITY_WEIGHTS` (`:100-132`).
**Signature:** `roll(userId: string): Roll`; `getCompanion(): Companion | undefined`.
**Data Shape:** Persisted = `StoredCompanion = CompanionSoul { name, personality } + { hatchedAt }` ONLY. Regenerated = `CompanionBones { rarity, species, eye, hat, shiny, stats }`. `RARITY_WEIGHTS = { common:60, uncommon:25, rare:10, epic:4, legendary:1 }`.

### Decisive source
```ts
// Regenerate bones from userId, merge with stored soul. Bones never persist
// so species renames and SPECIES-array edits can't break stored companions,
// and editing config.companion can't fake a rarity.
export function getCompanion(): Companion | undefined {
  const stored = getGlobalConfig().companion
  if (!stored) return undefined
  const { bones } = roll(companionUserId())
  // bones last so stale bones fields in old-format configs get overridden
  return { ...stored, ...bones }
}
```
with the seeded pipeline:
```ts
const SALT = 'friend-2026-401'
function hashString(s: string): number {
  if (typeof Bun !== 'undefined') return Number(BigInt(Bun.hash(s)) & 0xffffffffn)
  let h = 2166136261                       // FNV-1a fallback off Bun
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619) }
  return h >>> 0
}
// mulberry32(seed) — tiny seeded PRNG, good enough for picking ducks
let rollCache: { key: string; value: Roll } | undefined   // single-entry memo:
// called from three hot paths (500ms sprite tick, per-keystroke, per-turn)
```

**Flow:** `userId + SALT` → hash → mulberry32 stream → `rollRarity` (weighted total 100, walk RARITIES order subtracting weights, negative ⇒ that tier) → species/eye via `pick(rng, arr)` → hat (`'none'` FORCED on common) → shiny (`rng() < 0.01`) → stats → leftover `inspirationSeed = floor(rng()*1e9)` handed to the LLM soul-generator so name/personality are also seeded but stored.
**Invariant:** The user ID is the ENTIRE entropy source: same account always hatches the same bones on any machine, wiping config loses nothing derived, and hand-editing the config cannot upgrade rarity (derived fields overwrite whatever is stored — spread ORDER is the security boundary). Rarity floors lift stats (`RARITY_FLOOR` 5→50); one peak stat (`min(100, floor+50+rng*30)`), one dump stat (`max(1, floor-10+rng*15)`), rest scattered (`floor+rng*40`) — never uniform rolls.
**Probe:** No direct test file exists for `src/buddy/` (coverage caveat — claims source-grounded). Deterministic probe: `search_graph --project locoagent --name-pattern "^(roll|getCompanion)$"` resolves `locoagent.src.buddy.companion.roll` / `.getCompanion`; grep pins the spread comment at `src/buddy/companion.ts:131` and `SALT` at `:84`.

## Layered sprite frames with height stability
**Path/Symbol:** `src/buddy/sprites.ts`:`renderSprite`, `spriteFrameCount`, `renderFace` (`:454-514`); `src/buddy/types.ts`:species constants built via `String.fromCharCode` (`:14-52`).
**Signature:** `renderSprite(bones: CompanionBones, frame = 0): string[]`; `renderFace(bones): string`.
**Data Shape:** Every body = exactly 5 lines × 12 cols after `{E}`→eye substitution; ≥3 frames per species for idle fidget; line 0 is the HAT SLOT (must be blank in frames 0-1; frame 2 may use it for smoke/antenna).

### Decisive source
```ts
const lines = [...body]
// Only replace with hat if line 0 is empty (some fidget frames use it for smoke etc)
if (bones.hat !== 'none' && !lines[0]!.trim()) lines[0] = HAT_LINES[bones.hat]
// Drop blank hat slot — wastes a row... Only safe when ALL frames have blank
// line 0; otherwise heights oscillate.
if (!lines[0]!.trim() && frames.every(f => !f[0]!.trim())) lines.shift()
```

**Flow:** pick species frame array (`frame % frames.length` keeps any index valid) → substitute `{E}` placeholders with the eye glyph → hat paints only an EMPTY line 0 → collapse the blank top row only when EVERY frame agrees it is blank → blink renders by string-replacing the eye char with `-` on frame 0 (caller-side, see CompanionSprite). Narrow surfaces use `renderFace` one-liners (`(${eye}>` duck, `=${eye}ω${eye}=` cat, …) instead of scaling sprites.
**Invariant:** Rendered HEIGHT must never depend on the animation frame — either all frames carry a usable line 0 or none do; the shift guard checks ALL frames before dropping the row. Hats compose only into blank slots so fidget art is never overwritten. Frame math is modulo-based, so out-of-range indices wrap instead of throwing.
**Probe:** No direct test file (coverage caveat — source-grounded). Deterministic probe: `search_graph --project locoagent --name-pattern "^renderSprite$"` resolves `locoagent.src.buddy.sprites.renderSprite`; grep pins the all-frames guard at `src/buddy/sprites.ts:467`.

### Host quirk worth copying
Species literals are runtime-constructed (`String.fromCharCode(0x64,0x75,...)`) because ONE name collides with a model-codename canary grepped in BUILD OUTPUT (not source) — runtime construction keeps the literal out of the bundle while keeping the leak check armed (:10-13).

## Animation loop contract (consumer)
**Path/Symbol:** `src/buddy/CompanionSprite.tsx`:`TICK_MS/BUBBLE_SHOW/FADE_WINDOW/PET_BURST_MS/IDLE_SEQUENCE` (`:16-23`).
**Data Shape:** 500 ms tick; bubble shows 20 ticks (~10 s) with the last 6 dimmed (fade warning); idle sequence `[0,0,0,0,1,0,0,0,-1,0,0,2,0,0,0]` where `-1` means "blink on frame 0"; pet hearts burst for 2500 ms over 5 prepended heart rows.
**Flow:** reaction/pet ⇒ excited fast cycle through ALL frames; otherwise walk IDLE_SEQUENCE (mostly rest, occasional fidget, rare blink). Pet start uses sync-during-render state update (not useEffect) so the first post-pet render already has `petAge=0` — otherwise frame 0 of the burst is skipped. Fullscreen renders the speech bubble through the layout's bottomFloat slot because an absolute overlay gets clipped by `overflowY:hidden`, and non-fullscreen renders inline because floating content into Static scrollback cannot be cleared.
**Invariant:** All timing derives from TICK multiples, never wall-clock timeouts, so pause/resume stays coherent. The bubble clear timer lives with the component that owns the reaction; the floating variant only reads + fades.
**Probe:** No direct test file (coverage caveat — source-grounded). Deterministic probe: grep pins `TICK_MS = 500` and `IDLE_SEQUENCE` at `src/buddy/CompanionSprite.tsx:16-23` and the sync-during-render comment at `:186-188`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "companion roll mulberry32 renderSprite bones soul", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the derived-bones/stored-soul split with spread-order overriding, salted-hash→seeded-PRNG pipelines with a hot-path memo, fixed-grid sprite frames with the all-frames height-stability guard, and tick-derived animation timing. Adapt species/stat vocabularies, weights, and visual style to your product. Omit the React-compiler-optimized Ink components and the codename-canary obfuscation unless your host has the same build-time secret scanner; keep the derivation-not-storage principle everywhere.
