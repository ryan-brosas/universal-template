<!-- capsule-v2 -->
# LangGraph form-answer pipeline — how do I wire an LLM into application-form answering with option snapping and a structured-output fallback?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550`; Codebase Memory `Auto_job_applier_linkedIn`. **Question:** what is the full contract of `modules/ai/connections.py` — provider resolution, the compiled answer graph, and every degradation path?

## The AI answer layer
**Path/Symbol:** `modules/ai/connections.py` — `_resolve_provider` (:57–64), `_msg_text` (:80–98), `create_ai_client` (:107–152), `extract_skills` (:170–189), `_build_answer_graph` (:207–265), `answer_question` (:268–298); prompts in `modules/ai/prompts.py`; public surface consumed by `runAiBot.py:50`.
**Signature:** `answer_question(client, question, options=None, question_type='text', job_description=None, about_company=None, user_information_all=None) -> str` (empty string on any failure); `extract_skills(client, job_description) -> dict` (`{"error": ...}` dict on failure); `create_ai_client() -> AIClient | None` (None when `cfg.use_AI` false OR setup fails).
**Data Shape:** `_AnswerState` TypedDict (question/options/question_type/job_description/about_company/user_information → prompt/raw/answer); `ExtractedSkills` pydantic model with five list buckets (tech_stack/technical_skills/other_skills/required_skills/nice_to_have).

### Decisive source
```python
# one graph, conditional edge on question type; select snaps, text passes through
def select_option(state):
    raw = (state.get("raw") or "").strip(); options = state.get("options") or []
    for opt in options:                    # 1. exact
        if raw == opt: return {"answer": opt}
    low = raw.lower()
    for opt in options:                    # 2. case-insensitive
        if low == opt.lower(): return {"answer": opt}
    for opt in options:                    # 3. substring either direction
        if opt.lower() in low or low in opt.lower():
            return {"answer": opt}
    return {"answer": raw}                 # 4. honest passthrough — never fabricate a match
graph.add_conditional_edges("generate", route, {"text": "format_text", "select": "select_option"})

# structured output degrades to plain JSON parse for local/older models:
try:    return client.model.with_structured_output(ExtractedSkills).invoke(prompt).model_dump()
except: return convert_to_json(_msg_text(client.model.invoke(prompt)))
```

**Flow:** `_resolve_provider` collapses everything OpenAI-compatible (Ollama/LM Studio/DeepSeek/vLLM) onto the `openai` provider via base_url, gemini names onto `google_genai`, key `not-needed` placeholder when local; `build_prompt` appends JD/company context only when not `"Unknown"` plus a bullet-list option block; `generate` extracts text via `_msg_text` (handles `.text()` callable, str content, content-block dicts); failure anywhere lands in `answer_question`'s try/except returning `""` with an optional dismissible GUI alert that can pause itself.
**Invariant:** EVERY entry point is None-safe and fail-soft (`answer_question(None,...)==""`) because the bot must keep applying when AI is off; temperature stays UNSET unless the user opted in (some models reject non-defaults); option snapping never invents an answer — unmatched raw text passes through for downstream heuristics (qa-memory-ladder / phrase families in form-question-answering own the final choice).
**Probe:** `tests/test_ai_connections.py` — :89–93 stub-model text round-trip (" 5 "→"5"); :96–100 "Yes, absolutely"→snaps "Yes"; :103–107 no-match passthrough ("Maybe later" stays); :110–111 none-client safe; :120–124 structured payload equality; :127–131 stub without `with_structured_output` forces the JSON-parse fallback. All runner-free (stub `_StubModel`, no network).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "_build_answer_graph answer_question extract_skills", limit: 10 });
```

## Verdict
Adopt: single compiled graph with conditional select/text routing, exact→ci→substring→passthrough snapping ladder, structured-output-with-JSON-fallback, provider collapse to openai-compatible-by-base_url. Adapt prompts (prompts.py owns wording) and alert plumbing to host GUI. Omit pyautogui confirm dialogs in headless ports. Pass-11 note: pass 10 recorded this file as dead product code — WRONG at current HEAD `0ca5550`: it is the live AI layer behind runAiBot.py's question answering.
