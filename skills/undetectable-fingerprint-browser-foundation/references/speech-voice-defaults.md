<!-- capsule-v2 -->
# Speech voice defaults — at-most-one default voice, locale-coherent, 0..339 list spectrum

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** How must a profile populate `speechSynthesis.getVoices()` so voice-count and default-voice checks agree with the identity's locale?

## Path/Symbol
**Path/Symbol:** `fingerprints/fingerprints.db.xz` → `.speech[]` — entries `{voice_uri:int, lang:string, local_service:bool, default:bool}` where `voice_uri` is an integer index into a product-private table (resolver not in this repo). Graph caveat: `not_tracked` artifact; plane absent from node surface (Retrieve → total 0).

## Signature
**Signature:** `.speech` = `Array<{voice_uri:int, lang:string, local_service:boolean, default:boolean}>`, length 0..339 across the corpus.

## Data Shape
- List lengths span **0..339** (typical desktop lists 19–31; full 300+ lists exist).
- **Exactly-one-default holds on 9871/10000; 129 records carry NO default** — both cohorts are real.
- The flagged default is `local_service=true` on **9657/9871** flagged records; the remaining 214 carry a NON-local default voice (fresh guarded probe grouped `{true×9657, remainder 343}` where remainder = 129 no-default + 214 non-local). Locale coherence example from pass-3 census: ru-RU record with ru-RU default.
- Voice lists correlate with the identity's language plane (`user-agents.json` language field lives on the same doctrine); a zh-CN identity with an en-US-only voice list is a cross-plane tell.

### Decisive source
```jsonc
// fresh pass-7 stream probes (verbatim)
defaults     : [{"v":0,"n":129},{"v":1,"n":9871}]
local split  : [{"v":true,"n":9657},{"v":"nodefault","n":343}]   // 343 = 129 no-default + 214 non-local
len range    : {"min":0,"max":339}
```

**Flow:** take `.speech[]` verbatim from the chosen record → expose through `getVoices()` in recorded order → keep the at-most-one-default property and the record's own locale pairing.
**Invariant:** never synthesize a second default or strip the empty-list cohort; `default:true` must appear at most once, and when present it is overwhelmingly a LOCAL service voice of the record's own locale.

**Probe:** `xz -dc fingerprints/fingerprints.db.xz | jq -c '[.[] | ([.speech[] | select(.default == true)] | length)] | group_by(.) | map({v:.[0],n:length})'` → `[{"v":0,"n":129},{"v":1,"n":9871}]` (executed pass 7).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser",
  query: "speech synthesis voices default local_service language voice uri list" });
// executed pass 7 -> total: 0 (plane absent from node surface; this capsule is the only path)
```

## Verdict
Adopt the at-most-one-default invariant with its 129-record zero-default cohort; adapt `voice_uri` resolution to your own voice table (the original resolver ships with the binary only); omit locale-randomized voice lists. Caveat: per-language cohort censuses beyond the recorded examples are unverified at pin.
