<!-- capsule-v2 -->
# Typed compaction instructions — how do you accept machine instructions through an LLM-written channel without JSON.parse exposing you to prototype pollution or adversarial depth?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the fail-closed decode contract for a typed compaction request embedded in model output?

## Magic-prefix dispatch + hand-rolled strict JSON parser
**Path/Symbol:** `src/compaction/instructions.ts:decodeCompactionInstructions` (:368-476), `StrictJsonParser` (:171-366), bounds gate `compactionRequestBoundsError` (:85-126), encoder `encodeCompactionRequest` (:128-141); constants :3-9 (`FABRIC_COMPACTION_REQUEST_PREFIX = "__pi_fabric_compact_request_v1__:"`, 16 KiB encoded cap, 16 preserve items ×2 KiB).
**Signature:** `decodeCompactionInstructions(source?: string): {ok:true; requestLines:string[]; policy} | {ok:false; requestLines:[]; error:{code, message, sourceBytes}}`; policy mode ∈ `none|plain|typed-v1`; twelve typed error codes (:26-38).
**Data Shape:** typed request `{version:1, instructions?, preserve?: string[]}` rendered to lines: instructions verbatim, preserve as `- <item> [preserve:<index>]`.

### Decisive source
```ts
// No prefix → PLAIN prose: canonicalized, never parsed. The parser is used
// ONLY for the magic-prefixed channel.
if (!source.startsWith(FABRIC_COMPACTION_REQUEST_PREFIX)) return plainInstructions(source);
```
```ts
// StrictJsonParser: duplicate keys REJECTED (Object.create(null) target),
// depth ≤32, nodes ≤4096, control chars rejected, unpaired surrogates rejected
private parseObject(depth: number): Record<string, unknown> {
  ...
  const output = Object.create(null) as Record<string, unknown>;
  const keys = new Set<string>();
  ...
  if (keys.has(key)) throw new StrictJsonError("duplicate-field",
    `typed compaction request contains duplicate field ${JSON.stringify(key)}`);
```
```ts
const unknownField = keys.find((k) => k !== "version" && k !== "instructions" && k !== "preserve");
if (unknownField !== undefined) return rejection("unknown-field", …);
if (parsed.version !== 1)                        return rejection("unsupported-version", …);
```

**Flow:** empty → mode "none" → no prefix → plain canonicalization (whitespace-normalized free text, truncation recorded in policy) → prefixed: size-gate the WHOLE source (16 KiB) BEFORE parsing → strict-parse with structural caps → require plain object, closed key set, version===1, exact types → per-item surrogate + char/byte bounds → canonicalize each field, accumulating `truncated`/`canonicalized` flags into the policy. Every rejection returns `ok:false` with a typed code and byte count — the caller degrades to summary-without-instructions instead of crashing compaction.
**Invariant:** fail-closed on ANY deviation (unknown fields and duplicate fields are errors, not tolerated data) — the LLM-authored channel can never smuggle structure into the summarizer; `JSON.parse` is never used on model output here (prototype-pollution and __proto__ class eliminated by construction via Object.create(null) + allowlist); plain mode stays semantic-free ("Keep EXACT_fact" survives canonicalization without interpretation).
**Probe:** `tests/compaction.test.ts:447` ("decodes typed compact.request instructions and preserve items"; `:470` it.each fails closed for malformed-json / unsupported-version / unknown-field / invalid-type), `:501-507` (paired-surrogate acceptance vs raw unpaired rejection, encode throws), `tests/compact-controller.test.ts:150` (controller captures customInstructions through this decoder).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "decodeCompactionInstructions StrictJsonParser FABRIC_COMPACTION_REQUEST_PREFIX duplicate-field unsupported-version hasPairedSurrogates", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the prefix-dispatch (typed only behind an explicit sentinel), the hand-rolled strict parser with structural caps, and typed degradation codes; adapt limits and the request schema; omit nothing safety-bearing — replacing StrictJsonParser with JSON.parse silently reopens the duplicate-key/prototype surface. Direct tests cited; graph coverage clean.
