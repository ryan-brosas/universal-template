<!-- capsule-v2 -->
# Persona-guided conversation simulation — how does multi-perspective question asking actually terminate and stay grounded?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** How do simulated writer/expert dialogues end without loops, how is context bounded, and what keeps expert answers tied to search results?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/storm_wiki/modules/knowledge_curation.py:ConvSimulator.forward` (:47-81) + `WikiWriter.forward` (:95-125) + `TopicExpert.forward` (:204-244); personas `persona_generator.py:StormPersonaGenerator.generate_persona` (:134-154).
**Signature:** `forward(topic, persona, ground_truth_url, callback_handler) -> dspy.Prediction(dlg_history=List[DialogueTurn])`; `generate_persona(topic, max_num_persona=3) -> List[str]`.
**Data Shape:** Personas are strings `"Name: description"`; the colon split assigns role vs description (`ConversationTurn` twin does `role.split(":")`). Each turn carries `search_queries`, `search_results`, cited answer text.

### Decisive source
```python
# termination: sentinel string INSIDE the asker signature + empty-question guard
if user_utterance == "":
    logging.error("Simulated Wikipedia writer utterance is empty."); break
if user_utterance.startswith("Thank you so much for your help!"):
    break
# context windowing in WikiWriter: full answers ONLY for the last 4 turns
for turn in dialogue_turns[:-4]:
    conv.append(f"You: {turn.user_utterance}\nExpert: Omit the answer here due to space limit.")
conv = ArticleTextProcessing.limit_word_count_preserve_newline(conv, 2500)
# persona default: "Basic fact writer" ALWAYS first, then up to max_num_persona more:
considered_personas = [default_persona] + personas.personas[:max_num_persona]
```

**Flow:** Persona generator finds related wiki topics → scrapes their TOCs as inspiration → LLM lists numbered editor personas → default prepended → per-persona conversations run CONCURRENTLY (ThreadPoolExecutor, `max_workers=min(max_thread_num, len(personas))`, Streamlit ctx attached to threads when present) → each turn: writer asks → `QuestionToQuery` makes ≤max_search_queries queries → `retriever.retrieve(list(set(queries)), exclude_urls=[ground_truth_url])` → expert answers citing `[n]` over top-1-snippet-per-result info capped at 1000 words.
**Invariant:** (1) The "Thank you…" sentinel is a PROMPT-side contract — changing the signature text breaks termination. (2) Ground-truth URL exclusion prevents evaluation leakage through EVERY turn's retrieval. (3) Expert refusal paths are explicit strings on zero results or answer failure — never silent. (4) Queries deduped via `set()` before retrieval; per-query citation markers are assigned AFTER retrieval by enumerate order, so result order is load-bearing.
**Probe:** deterministic pins GREEN — knowledge_curation.py:64-67 sentinel/empty guards and :217-240 grounded-refusal ladder byte-read this pass; conv-window 2500-word cap at :113.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "ConvSimulator TopicExpert ground truth", limit: 10 });
```

## Verdict
Adopt the sentinel-termination + sliding-window dialogue pattern and the always-first default persona for multi-perspective research agents; adapt persona count/sentinel phrasing; omit the Streamlit thread-context shim outside streamlit hosts. Caveat: no upstream tests; source-pinned.
