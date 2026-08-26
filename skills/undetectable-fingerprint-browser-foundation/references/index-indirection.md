<!-- capsule-v2 -->
# Index indirection — why are fonts/headers/codecs/user_agent stored as integer indexes?

**Source:** itbrowser-net/undetectable-fingerprint-browser no-LICENSE `main@6df77401149f82fa089589946859a92a0d9f6bb7`; Codebase Memory `undetectable-fingerprint-browser`. **Question:** When consuming the profile database, how must integer-valued fields be resolved before injection?

## Normalized vocabularies, resolved outside the record
**Path/Symbol:** `fingerprints/fingerprints.db.xz` stream fields: `.navigator.user_agent` (=1), `.webgl.extensions` ([0..28]), `.webgl.extensions2`, `.fonts[]`, `.headers[]`, `.codecs[]` ([0..5]). Graph coverage caveat: binary artifact, freshness "not_tracked" — direct-stream evidence only.
**Signature:** index-bearing fields are `number | number[]` — including, per pass-2 census, `.webrtc.*.codecs[].mimeType` (compact-form values 13 video / 20 audio) and `.webrtc.*.extensions[].uri` (`10`) inside the db stream; inline-string siblings (`brands`, `unmasked_renderer`, RICH-webrtc codec mimeTypes) stay literal. Whether a field is indexed is a PER-PLANE, PER-COHORT property — never assume from the field name alone.
**Data Shape:** measured in-stream: `"user_agent":1`, `"extensions":[0,1,...,28]` / `"extensions2":[29,2,30,...]`, fonts arrays of hundreds of ints, codecs [0..5], headers [0..33]; db `navigator.user_agent` spans 0..219 with 102 distinct values used across 10,000 records. Compression context: xz stream is 1.29 MiB → 210.9 MiB (~163x).

### Decisive source
```jsonc
"navigator":{"user_agent":1, ...},
"webgl":{ ..., "extensions":[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28],
          "extensions2":[29,2,30,4,7,8,9,31,11,32,16,33,21,22,23,24,27,28,34], ...}
```

**Flow:** load profile → keep inline strings as-is → resolve each index field against its global vocabulary table → inject resolved values; never inject bare integers.
**Invariant:** indexes are stable ONLY against the vocabulary version they were captured with; a resolver/table mismatch silently produces a different identity than the record encodes. JOIN HYPOTHESIS TESTED AND REFUTED (pass 2): `navigator.user_agent` does NOT index into `fingerprints/user-agents.json` positional order — db idx 2 ⇒ Windows-platform records while user-agents.json[2] is an iPhone profile (json[0]=Linux armv81, [1]=Win32); every db UA-index cohort is platform-"Windows" over a 0..219 range, i.e. the vocabulary is product-private AND OS-partitioned. The pass-1 claim that codec mimeType stays inline was likewise corrected by census: compact-form webrtc slots index it.
**Probe:** `xz -dc fingerprints/fingerprints.db.xz | jq -c '{ua_range: ([.[] | .navigator.user_agent] | {min: min, max: max, distinct: (unique|length)})}'` → `{ua_range:{min:0,max:219,distinct:102}}`; and `jq -c '.[2].platform' fingerprints/user-agents.json` → an iPhone record, refuting positional alignment (both executed pass 2). Pass-1 probe: `xz -dc fingerprints/fingerprints.db.xz | strings -n 8 | grep -o '"user_agent":[0-9]*' | head -3` → integers pin the indirection pattern.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "undetectable-fingerprint-browser", name_pattern: "^extensions2?$", label: "Variable", limit: 5 });
```

## Verdict
Adopt the design principle: factor repeated vocabularies (UA strings, GL extension enums, font catalogs, header orderings) into versioned tables and store indexes — this is what makes 163x compression plus fleet-wide consistency possible; adapt by defining your own tables when regenerating profiles; omit any claim that user-agents.json or another repo file resolves a given index — the join was TESTED and refuted at this pin (see Invariant), and all non-inline resolver tables ship with the closed binary and remain unverifiable here.
