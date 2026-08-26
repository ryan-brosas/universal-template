<!-- capsule-v2 -->
# LLM JSON salvage ladder — how do you parse near-JSON out of an LLM that keeps breaking JSON?

**Source:** paper-qa Apache-2.0 `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** In what ORDER must malformed-LLM-JSON repairs be applied so that fenced output, prose wrappers, fractions-as-scores, missing commas, and raw-newlines-in-strings all parse without corrupting valid JSON?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/core.py:llm_parse_json` (:19-124).
**Signature:** `def llm_parse_json(text: str) -> dict[str, JsonValue]`.
**Data Shape:** Arbitrary LLM completion text in; dict out. Raises `ValueError("Failed to load JSON from text ...")` when nothing salvageable remains. Two magic keys are enforced downstream: `summary` (str) and `relevance_score` (int).

### Decisive source
```python
ptext = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()   # 1 reasoning tags
ptext = ptext.split("```json")[-1].split("```")[0]                          # 2 json fence
if "{" not in ptext and "}" not in ptext:
    ptext = json.dumps({"summary": ptext})                                  # 3 prose → wrapper
ptext = ("{" + ptext.split("{", 1)[-1]).rsplit("}", 1)[0] + "}"             # 4 first{..last}
ptext = re.sub(r'"(?:[^"\\]|\\.)*"', escape_newlines)                        # 5 \n inside strings ONLY
ptext = re.sub(r'\\([^"\\/bfnrtu])', r"\\\\\1", ptext)                      # 6 invalid escapes doubled
# 7 fraction scores "8/10"|"5/10"-quoted-or-not → round(n/d*10)
ptext = re.sub(r'("\s*(?:relevance|score)[\w\s\-]*"\s*:\s*)(?:"(\d+)\s*/\s*(\d+)"|(\d+)\s*/\s*(\d+))',
               fraction_replacer, ptext)
ptext = re.sub(r'(?<=[}\]0-9"])\s*(?="[^"\\]*"\s*:)', ", ", ptext)          # 8 insert missing commas
data = json.loads(ptext)  # then: rename any *relevance|score* key → relevance_score (:110-112);
                          # coerce float/str score via round(float(x)) (:115-122)
# LAST resort (:95-105): regex-extract "summary" and "relevance_score" independently
```

**Flow:** think-strip → fence-isolate → prose-wrap → brace-isolate → string-scoped newline escape → escape repair → score-fraction normalization → comma insertion → strict parse → per-field regex salvage → typed coercion. Step 4 runs AFTER prose-wrap so pure-prose becomes `{"summary": ...}` and survives.
**Invariant:** Repairs are ordered cheapest/most-specific first; newline escaping must be scoped inside string literals (step 5) or real multiline strings get corrupted; the final regex salvage only fires for the known two-key shape.
**Probe:** `tests/test_paperqa.py` TestLLMParseJSON classes (:3197 basic_json_extraction, :3260 relevance_score_parsing, :3304 json_keys, :3338 broken_formatting, :3355 fallback_non_json, :3366 escaped_characters); executed lifted probe T3a–T3e GREEN (fence+fraction `"8/10"`→8, prose-wrap, missing-comma repair, key rename, hard-raise).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "llm_parse_json fraction_replacer escape_newlines", limit: 10 });
```

## Verdict
Adopt the whole ladder verbatim — the order IS the contract; adapt the two magic keys to your schema; omit the `relevance_score` fraction special-case if your prompt forbids fraction scores. Direct tests exist upstream and were mirrored by executed lifted probes.
