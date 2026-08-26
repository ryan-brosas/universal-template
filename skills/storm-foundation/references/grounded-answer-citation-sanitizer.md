<!-- capsule-v2 -->
# Grounded-answer citation sanitizer — how do you keep an LLM's inline `[n]` markers honest against what was actually retrieved?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** What is the minimal post-processing chain that turns raw LLM answers into text whose citations provably reference retrieved sources?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/utils.py:ArticleTextProcessing` (:301-594) — `remove_uncompleted_sentences_with_citations` (:367-425), `remove_citations` (:337-350), `clean_up_citation` (:428-454); consumer `TopicExpert.forward` (knowledge_curation.py:228-240).
**Signature:** `remove_uncompleted_sentences_with_citations(text: str) -> str`; `remove_citations(s: str) -> str`.
**Data Shape:** Answers carry inline `[1]`, grouped `[1, 2]` citations produced by the `AnswerQuestion` signature; each turn stores the search results the numbers refer to.

### Decisive source
```python
# 1. split groups: "[1, 2, 3]" -> "[1] [2] [3]"
text = re.sub(r"\[([0-9, ]+)\]", replace_with_individual_brackets, text)
# 2. dedupe+sort runs of adjacent citations: "([d+])+" -> sorted unique
text = re.sub(r"(\[\d+\])+)", deduplicate_group, text)
# 3. truncate at the LAST sentence-final punctuation (+optional citation):
eos_pattern = r"([.!?])\s*(\[\d+\])?\s*"
matches = list(re.finditer(eos_pattern, text))
if matches:
    text = text[: matches[-1].end()].strip()
# hallucination gate in clean_up_citation — refs beyond the turn's sources are STRIPPED:
if max_ref_num > len(turn.search_results):
    for i in range(len(turn.search_results), max_ref_num + 1):
        turn.agent_utterance = turn.agent_utterance.replace(f"[{i}]", "")
```

**Flow:** Expert answers are truncated to the last complete sentence (dropping token-limit cut-offs mid-citation), grouped citations normalized to individual sorted-unique form, and in `clean_up_citation` any number exceeding the turn's actual `search_results` count is deleted; `References:`/`Sources:` trailing sections are amputated before counting. The no-evidence path refuses explicitly ("Sorry, I cannot find information...") instead of answering ungrounded.
**Invariant:** (1) Sanitize BEFORE storing the DialogueTurn — downstream merge/retrieval assumes every surviving `[n]` has a backing source. (2) The max-ref strip is per-TURN (`turn.search_results`), not global. (3) `remove_citations` must run when snippets are fed as CONTEXT (WikiWriter history, outline conv) so source-side brackets don't pollute the next generation's citation vocabulary. (4) Truncation keeps only up to last `.!?`(+citation) — an uncited trailing clause after the final cited sentence is discarded.
**Probe:** executed lifted probes GREEN — T01 `remove_citations("a[1] b[2, 3] c") == "a b c"`; T06 truncation `"Done[1]. Partial[2"` → `"Done[1]."`, kept-sentence case; T08 single-number-only parse (scratch-storm-pass1/probe_gate5.py).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "remove_uncompleted_sentences_with_citations eos", limit: 10 });
```

## Verdict
Adopt the normalize→truncate→range-strip ladder verbatim as the minimum honest-citation gate; adapt thresholds/punctuation set; omit the deprecated commented sentence-splitter block (:400-416). Caveat: no upstream tests; probes executed against AST-lifted class source.
