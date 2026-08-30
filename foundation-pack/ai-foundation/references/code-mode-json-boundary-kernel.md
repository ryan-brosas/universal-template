<!-- capsule-v2 -->
# Code-mode JSON boundary kernel — empty-string undefined protocol, strict serialization, and byte-exact size gates

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How do values cross the sandbox↔host bridge, and what are the exact JSON semantics at each edge?

## String-payload protocol with sentinel
**Path/Symbol:** `packages/code-mode/src/utils/serialization.ts` whole (:3–70); call sites run-code-mode.ts:129–131 (result), :309–313 (tool input), tool-invocation.ts:159–166 (tool output).
**Signature:** `toJsonPayload(undefined) === ''`; `fromJsonPayload('') === undefined`; everything else = strict `JSON.stringify` + TextEncoder byte-length check.
**Data Shape:** bridge carries STRINGS, not values — every boundary is (value → string → [size gate] → string → value).

### Decisive source
```ts
export function toJsonPayload(value: unknown, maxBytes: number, label: string): string {
  if (value === undefined) return '';          // '' is the undefined sentinel
  return toStrictJsonPayload(value, maxBytes, label);
}
export function assertJsonSerializable(value, maxBytes, label): void {
  void toJsonPayload(value, maxBytes, label);  // validate-only twin
}
```

**Flow:** results: sandbox already returns `JSON.parse(JSON.stringify(x))` (JSON.stringify semantics: Infinity→null, functions in objects dropped — pinned by exceptions.test.ts:110–126) → host round-trips through toJsonPayload(maxResultBytes) so the SIZE GATE applies to the escaped wire form. Tool inputs: sandbox argument → toJsonPayload(maxToolInputBytes) BEFORE crossing → parsed + re-validated on host. Tool outputs: execute result → toJsonPayload(maxToolOutputBytes) → string back into sandbox. Failures are typed `CODE_MODE_SERIALIZATION_ERROR` with `{bytes,maxBytes}` details; circular inputs die at stringify with a message matching `/circular|closes the circle/` before any execute (test :128–147 pins execute-not-called). Date outputs become ISO strings via stringify semantics (test :209–221); undefined object properties silently omitted (:223–245).
**Invariant:** the empty-string sentinel means the protocol CANNOT distinguish "returned undefined" from an empty payload — any porter extending the bridge with new value types must preserve this or break the `round-trips undefined tool outputs` contract (test :57–69 returns `{type:'undefined'}`). Size checks use TextEncoder byteLength, never `.length` — multibyte content counts real bytes.
**Probe:** deterministic (repo root): `grep -nF "valueJson === '" packages/code-mode/src/utils/serialization.ts` → matches line 24 (`return valueJson === '' ? undefined : JSON.parse(valueJson);`); `grep -nF 'new TextEncoder().encode' packages/code-mode/src/utils/serialization.ts` → `58:`; `grep -cF 'CODE_MODE_SERIALIZATION_ERROR' packages/code-mode/src/utils/serialization.ts` → `3`; direct-test anchors: exceptions.test.ts:116 (`{value:null}`), :125 (`{}`), :220 (ISO date string), exceptions.test.ts `size limit` greps ×3 (`grep -cF 'rejects.toThrow(/size limit/)' packages/code-mode/src/exceptions.test.ts` → `3`).
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "ai", query: "toJsonPayload fromJsonPayload assertJsonSerializable", limit: 3 });` // verified family live @9d9a73f: serialization utils resolve under code-mode module nodes; canonical-json sibling at ai.packages.ai.src.util.canonical-hash.canonicalJSON :10-26

## Verdict
Adopt the string-payload bridge with sentinel-undefined and byte-exact gates; adapt limits freely (they're policy); omit nothing — length-vs-bytes and pre-execute gating are the two classic wrong ports.
