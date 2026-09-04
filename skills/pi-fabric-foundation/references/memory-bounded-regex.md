<!-- capsule-v2 -->
# Untrusted regex isolation — how do you let a user run regex search over your indexes without ReDoS or OOM taking down the host?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the containment envelope for user-supplied regex patterns, and how does query planning keep literal input from ever being compiled?

## Disposable worker + hard timeout + explicit-mode planning
**Path/Symbol:** `src/memory/regex.ts:executeBoundedRegex` (:39-110+), `WORKER_SOURCE` (:17); planner `planMemoryQuery` in `src/memory/tokenize.ts:24-31`.
**Signature:** `executeBoundedRegex(pattern: string, haystacks: string[], limits: {maxPatternBytes; timeoutMs}): Promise<{complete: true; matched: number[]} | {complete: false; matched: []; error: {code: "invalid_regex"|"regex_pattern_too_large"|"regex_timeout"|"regex_worker_error"; message}}>`; `planMemoryQuery(query, queryMode = "literal"): {kind:"browse"} | {kind:"terms"; terms[]} | {kind:"regex"; pattern}`.
**Data Shape:** worker built from an inline `eval:true` source with `resourceLimits: {maxOldGenerationSizeMb: 16, maxYoungGenerationSizeMb: 4}`; worker tests each haystack and posts back integer indices only.

### Decisive source
```ts
if (patternBytes > limits.maxPatternBytes) return { complete: false, matched: [],
  error: { code: "regex_pattern_too_large", message: `…limit is ${limits.maxPatternBytes}.` } };
...
const timer = setTimeout(() => finish({
  complete: false, matched: [],
  error: { code: "regex_timeout", message: `Regex execution exceeded ${limits.timeoutMs} ms.` },
}), limits.timeoutMs);
const finish = (result) => { if (settled) return; settled = true;
  clearTimeout(timer); void worker.terminate(); resolve(result); };   // ALWAYS terminate
```
```ts
// tokenize.ts — "Plan only the explicitly selected query mode.
//  Literal input is never compiled as regex."
if (queryMode === "regex") return { kind: "regex", pattern: query };
return { kind: "terms", terms: [...new Set(tokenizeLexical(query))] };
```

**Flow:** reject oversized patterns synchronously → spawn a throwaway heap-capped worker per query → race worker message against the timeout; whichever finishes first terminates the worker and clears the timer (single-settled guard) → every failure path (invalid pattern, worker error, invalid result shape, spawn failure) resolves to a typed `complete:false` error rather than rejecting. The planner only produces a regex plan when the caller explicitly selected regex mode; dots in paths like `src/foo.ts` stay literal terms.
**Invariant:** no unbounded regex ever executes on the main thread — heap caps + forced termination bound both memory and time; results are index lists only (no match text crossing the boundary). Mode selection is explicit and sticky: absence of `regex` flag can never promote a literal to a pattern.
**Probe:** `tests/memory-hardening.test.ts:87` ("never infers regex mode from dots or paths"), `:99` ("runs explicit regex in a bounded worker and terminates catastrophic patterns"); planner pinned at `tests/memory-hardening.test.ts:88` (`planMemoryQuery("src/foo.ts")` → `{kind: "terms", terms: ["src","foo","ts"]}`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "executeBoundedRegex worker terminate resourceLimits planMemoryQuery regex literal", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the disposable heap-capped worker + typed fail-closed results + explicit-mode query planning trio for any user-regex surface; adapt limits and error codes; omit Node Worker specifics if your host isolates differently (but keep SOME hard kill).
