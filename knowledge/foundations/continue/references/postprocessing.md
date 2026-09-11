<!-- capsule-v2 -->
# Completion postprocessing — the final safety net that rejects degenerate model output

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** After streaming, what deterministic checks reject or repair a completion before it is shown, and how are model-specific quirks (Codestral/Qwen3/Granite/Mercury/Gemini) handled?

## The postprocess gate
**Path/Symbol:** `core/autocomplete/postprocessing/index.ts:postprocessCompletion` (92–200).
**Signature:** `postprocessCompletion({completion, llm, prefix, suffix}): string | undefined`.
**Data Shape:** returns `undefined` to reject (empty, whitespace-only, repeats line above, extreme repetition); otherwise returns a repaired completion string.

### Decisive source
```ts
if (isBlank(completion)) return undefined;          // empty
if (isOnlyWhitespace(completion)) return undefined; // /^[\s]+$/
if (rewritesLineAbove(completion, prefix)) return undefined; // first completion line repeats the last non-blank prefix line
if (isExtremeRepetition(completion)) return undefined; // LCS-based multi-line repetition detector
// Model-specific repairs:
if (llm.model.includes("codestral")) { /* strip leading space if prefix ends space & suffix starts \n; strip leading \n after \n\n with empty suffix */ }
if (llm.model.includes("qwen3")) { completion = completion.replace(/ thinking.*?<\/think>/s, ""); completion = completion.replace(/<\/think>/, ""); completion = completion.replace(/^\n+|\n+$/g, ""); }
if (llm.model.includes("granite")) { /* strip repeated prefix-end / last word from completion start */ }
if (llm.model.includes("mercury") && (completion.startsWith("  ")||completion.startsWith("\t")) && !prefix.endsWith("\n") && (suffix.startsWith("\n")||suffix.trim().length===0)) completion = "\n"+completion;
if ((llm.model.includes("gemini")||llm.model.includes("gemma")) && completion.endsWith("<|file_separator|>")) completion = completion.slice(0,-18);
if (prefix.endsWith(" ") && completion.startsWith(" ")) completion = completion.slice(1);
completion = removeBackticks(completion); // strip ``` / ```lang first line and lone ``` last line
return completion;
```

**Flow:** reject empty/whitespace/line-repeat/extreme-repetition first (these are `undefined`), then apply model-name-keyed repairs (Codestral spacing, Qwen3 think-tag stripping, Granite prefix-repeat stripping, Mercury newline insertion, Gemini/Gemma file-separator removal), then the generic leading-space dedup and markdown backtick removal.

**Invariant:** `isExtremeRepetition` uses `longestCommonSubsequence(lines[0], lines[freq])` — if the LCS is >5 chars or >50% of line 0, and the repeated match spans >8 lines or >80% of the completion, reject; `removeBackticks` only strips a first line starting with ` ``` ` and a LAST line that is ALL backticks (`/^`+$/`), never backticks mid-line.

**Probe:** `core/autocomplete/postprocessing/index.test.ts` — 11 cases: removes first+last backtick lines, only-first, only-last, no modification without backticks, backticks in the middle preserved, leading whitespace before ` ``` `, whitespace around last ` ``` `, single line, empty→undefined, and `const x = 5; // end``` ` NOT stripped (backticks not on own line).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "postprocessCompletion removeBackticks", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the reject-then-repair ordering, the model-name-keyed repair table, the LCS repetition detector, and the markdown backtick stripper; adapt the model-name substrings and threshold constants to host; omit nothing portable here — it is a pure function of (completion, llm, prefix, suffix). Coverage caveat: graph metadata `metadata_match`; direct vitest suite exists.
