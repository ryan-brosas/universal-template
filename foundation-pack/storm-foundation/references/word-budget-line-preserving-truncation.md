<!-- capsule-v2 -->
# Word-budget line-preserving truncation — why must context-window clamping cut at newline boundaries?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** What is the exact algorithm for capping prompt context by word count without ever emitting a partial line?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/utils.py:ArticleTextProcessing.limit_word_count_preserve_newline` (:303-334); call sites WikiWriter conv (:113, 2500), TopicExpert info (:224, 1000), outline conv (:106, 5000), section writer (:152, 1500).
**Signature:** `limit_word_count_preserve_newline(input_string: str, max_word_count: int) -> str`.
**Data Shape:** Words = space-separated within a line; lines = `\n`-separated; output is a prefix of whole lines (plus possibly a final partial LINE only if it started before the budget).

### Decisive source
```python
word_count = 0
limited_string = ""
for word in input_string.split("\n"):        # iterating LINES (variable misleadingly named)
    line_words = word.split()
    for lw in line_words:
        if word_count < max_word_count:
            limited_string += lw + " "
            word_count += 1
        else:
            break                            # stop mid-line, no partial words
    if word_count >= max_word_count:
        break                                # but the NEXT line never starts
    limited_string = limited_string.strip() + "\n"   # re-seal completed lines
return limited_string.strip()
```

**Flow:** Iterate lines; append whole words until budget hit; when the budget lands mid-line, that line keeps its already-accepted complete words and the loop breaks — the next line NEVER begins, so no dangling fragment line survives; trailing spaces/newlines stripped.
**Invariant:** (1) Output word count ≤ budget AND output contains at most one line whose word count was clipped. (2) The four call-site budgets (5000/2500/1500/1000) are tuned to each prompt's role — outline history gets 5× the section-writer's evidence budget; preserve the ratio logic when porting. (3) Naive `split()`-then-join destroys newlines and merges unrelated turns/paragraphs — the newline structure carries speaker-turn and snippet boundaries in every consumer.
**Probe:** executed lifted probe GREEN — T02 `"one two\nthree four five", 3 → "one two\nthree"` and negative case (scratch-storm-pass1/probe_gate5.py).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "limit_word_count_preserve_newline", limit: 10 });
```

## Verdict
Adopt verbatim for any multi-source prompt assembly where lines carry semantic boundaries; adapt budgets per role; omit nothing. Companion dspy-context idiom used at every call site: `with dspy.settings.context(lm=self.engine)` scopes WHICH LM answers a given module — port it as explicit engine-per-call threading. Caveat: no upstream tests; probe executed against lifted class source.
