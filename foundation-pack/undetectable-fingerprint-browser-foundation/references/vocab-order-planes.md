<!-- capsule-v2 -->
# Vocabulary order planes — header order is data, codecs are a constant, keyboard has an empty cohort

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** Which of the index-array vocabularies (headers/codecs/keyboard/fonts) carry per-profile information versus pack constants a porter must not perturb?

## Path/Symbol
**Path/Symbol:** `fingerprints/fingerprints.db.xz` → `.headers[]` (string array), `.codecs[]` (int array), `.keyboard{}` (char→int-code map), `.fonts[]` (int array; spectrum in fonts-length-spectrum). Graph caveat: `not_tracked` artifact; planes absent from node surface (Retrieve → total 0).

## Signature
**Signature:** `.headers = string[31..37]`; `.codecs = int[6]`; `.keyboard = Record<char,int>` sized 0/43/47/48/49.

## Data Shape
- **Header ORDER is per-profile data:** lengths 31..37 with full ladder `{34×8061, 35×1697, 36×201, 33×25, 32×12, 37×3, 31×1}`, but only **62 distinct orderings** across 10,000 records — the sequence itself (e.g., which position Accept-Language occupies) is captured identity.
- **`.codecs[] == [0,1,2,3,4,5]` on ALL 10000 records** — one form, zero information. Randomizing it breaks pack coherence for no gain.
- **Keyboard sizes** `{0:492, 47:8767, 48:658, 49:74, 43:9}`: the EMPTY-keyboard cohort (492 records) is itself a detector-visible signature; 47–49 keys is the standard US layout mass.

### Decisive source
```jsonc
// fresh pass-7 stream probes (verbatim)
hdr lens   : [{"v":34,"n":8061},{"v":35,"n":1697},{"v":36,"n":201},{"v":33,"n":25},
              {"v":32,"n":12},{"v":37,"n":3},{"v":31,"n":1}]
orders     : 62
codec forms: [{"v":"[0,1,2,3,4,5]","n":10000}]
kb sizes   : {"0":492,"43":9,"47":8767,"48":658,"49":74}
```

**Flow:** emit `.headers[]` in the record's own order → copy codecs verbatim → map keyboard codes through your resolver only if you can resolve the same char→code table, else keep raw pairs consistent with the cohort size.
**Invariant:** header ORDER and membership move together as one captured unit (62 canonical sequences); codecs are frozen; the empty keyboard cohort must survive round-trips untouched.

**Probe:** `xz -dc fingerprints/fingerprints.db.xz | jq -c '[.[] | .headers|join("|")] | unique | length'` → `62` (executed pass 7); and `xz -dc fingerprints/fingerprints.db.xz | jq -c '[.[] | .keyboard|length] | group_by(.) | map({(.[0]|tostring):length}) | add'` → `{"0":492,"43":9,"47":8767,"48":658,"49":74}` (executed pass 7).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser",
  query: "header order Accept-Language keyboard key code codecs enumeration fonts array" });
// executed pass 7 -> total: 0 (plane absent from node surface; this capsule is the only path)
```

## Verdict
Adopt order-as-data for headers, the frozen codec enumeration, and the empty-keyboard cohort; adapt token resolution to your own vocabulary tables; omit re-sorting headers alphabetically or "completing" empty keyboards. Caveat: per-token vocabulary values resolve outside this repo (index-indirection caveat).
