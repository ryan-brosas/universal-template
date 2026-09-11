<!-- capsule-v2 -->
# Async CLI question channel — how do you ask the human a blocking question from inside an async event loop?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** What is the minimal async pattern for stdin input that never blocks the loop, and what state does it leave behind?

## Executor-offloaded input() returning a Future, keyed by full question string
**Path/Symbol:** `core/utils/cli_helper.py` (`:1-34`, whole file).
**Signature:** `def async_input(prompt: str) -> Future` / `async def answer_questions_over_cli(questions: list[str]) -> dict[str, str]`.
**Data Shape:** `loop.run_in_executor(None, input, prompt)` → concurrent.futures.Future (NOT asyncio.Future despite the annotation — the `# type: ignore` hides the lie). Answers dict is keyed by the ENTIRE question string.

### Decisive source
```python
# :15-16 — the whole trick
loop = asyncio.get_event_loop()
return loop.run_in_executor(None, input, prompt)

# :31-32 — sequential awaits; one answer per question, dict-keyed by question
for question in questions:
    answers[question] = await async_input("Question: "+str(question)+" : ")
```
**Flow:** `answer_questions_over_cli` prints an asterisk banner, asks each question in order, awaits each `run_in_executor` future (the default ThreadPoolExecutor absorbs the blocking `input()` so the event loop keeps serving Playwright/agent tasks), then closes with a second banner and returns the mapping.
**Invariant:** Offload blocking stdin I/O to an executor thread — never `await asyncio.to_thread`-less raw `input()` inside the loop (it freezes browser automation mid-run). Duplicate questions silently collapse to one answer (dict keying); EOF/KeyboardInterrupt inside the executor thread surfaces as an exception at the await site. **Status at pin: DEAD CODE** — zero import sites repo-wide (`grep -rn "cli_helper" core/ --include='*.py'` returns only the file itself). It documents the intended interactive-question channel that GUI mode replaced with the overlay's `user_response` exposed function + `user_response_event`; keep as reference vocabulary for headless ports.
**Probe:** `grep -c run_in_executor core/utils/cli_helper.py` → `1`; `grep -rn "from core.utils.cli_helper" core/ --include='*.py' | wc -l` → `0` (dead-code ruling evidence). Coverage caveat: no upstream tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "async_input answer_questions_over_cli executor", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt the executor-offload pattern when porting needs a headless question channel; wire it into your orchestrator yourself (upstream never did). Omit as dead code from any faithful behavioral clone of this pin. Coverage caveat: no upstream tests.
