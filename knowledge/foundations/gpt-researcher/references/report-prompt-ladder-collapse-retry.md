<!-- capsule-v2 -->
# Report prompt ladder + role-collapse retry — how does the final report call pick its prompt, embed pre-generated images, and survive providers that reject system messages?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** When porting the final report-writing call, which prompt wins for a given report_type, how do pre-generated images reach the model, and what happens when the provider rejects the system/user message split?

## generate_report three-arm prompt ladder + single collapse retry
**Path/Symbol:** `gpt_researcher/actions/report_generation.py:209-309` (`generate_report`), `gpt_researcher/prompts.py:862-876` (`get_prompt_by_report_type`), `gpt_researcher/skills/writer.py:49-134` (`ReportGenerator.write_report`).
**Signature:** `async def generate_report(query, context, agent_role_prompt, report_type, tone, report_source, websocket, cfg, main_topic="", existing_headers=[], relevant_written_contents=[], cost_callback=None, custom_prompt="", headers=None, prompt_family=PromptFamily, available_images=None, **kwargs) -> str`.
**Data Shape:** `available_images` items are `{url, title|alt_text, section_hint}` dicts; `existing_headers` is a list of `{"subtopic task", "headers"}` dicts from prior subtopics; `custom_prompt` is raw user text; all LLM spend goes through `cost_callback` (the researcher's `add_costs` step bucket).

### Decisive source
```python
# report_generation.py:253-258 — ladder order is fixed: subtopic > custom > default
if report_type == "subtopic_report":
    content = f"{generate_prompt(query, existing_headers, relevant_written_contents, main_topic, context, ...)}"
elif custom_prompt:
    content = f"{custom_prompt}\n\nContext: {context}"
else:
    content = f"{generate_prompt(query, context, report_source, ...)}"
```
```python
# report_generation.py:274-307 — system+user first; on ANY exception retry ONCE with roles collapsed
try:
    report = await create_chat_completion(model=..., messages=[
        {"role": "system", "content": f"{agent_role_prompt}"},
        {"role": "user", "content": content}], temperature=0.35, stream=True, ...)
except Exception:
    try:
        report = await create_chat_completion(model=..., messages=[
            {"role": "user", "content": f"{agent_role_prompt}\n\n{content}"}], ...)
    except Exception as e:
        print(f"Error in generate_report: {e}")
return report   # stays "" if both attempts failed
```
```python
# prompts.py:866-875 — unknown report_type warns and falls back to research_report prompt
prompt_by_type = getattr(prompt_family, report_type_mapping.get(report_type, ""), None)
if not prompt_by_type:
    warnings.warn(f"Invalid report type: {report_type}... Using default report type: {default_report_type} prompt.", UserWarning)
    prompt_by_type = getattr(prompt_family, report_type_mapping.get(default_report_type))
```

**Flow:** `write_report` first streams collected images to the client (`stream_output("images","selected_images",...)` :65-75) → abstention gate (see writer-abstention-gate) → copies `research_params`, re-derives empty `agent_role_prompt` as `cfg.agent_role or role` (:108-109) → subtopic researchers additionally inject `main_topic`/`existing_headers`/`relevant_written_contents` (:114-120) → `generate_report` resolves the prompt via the ladder → appends an "AVAILABLE IMAGES" block to the USER message listing each image as exact markdown `![title](url)` with its section_hint and instructing verbatim reuse (:261-273) → system+user call at temperature 0.35 → on exception, ONE retry collapsing both roles into a single user message → second failure prints and returns "".
**Invariant:** the collapse retry exists because some providers reject `system` role messages — dropping it makes those providers fail the whole report instead of degrading to a single-role call. The retry is provider-tolerance, NOT content repair: same content, same temperature, no backoff. Unknown report types must warn (UserWarning) and fall back to the research_report prompt, never raise — hosts pass free-form strings. Image instructions go in the user message, never the system message, so they survive the collapse retry intact.
**Probe:** byte anchors verified at pin: report_generation.py:253-258 (ladder), :261-273 (image block), :290-307 (collapse retry), :309 (`return report`); prompts.py:866-875 (warn-and-default); writer.py:65-75 (image pre-send), :108-122 (param injection). Coverage caveat: NO upstream test pins generate_report directly (grep of tests/ found none) — probe is source-read only; runner BLOCKED in-lane (missing aiofiles, read-only checkout).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-researcher", query: "generate_report get_prompt_by_report_type custom_prompt available_images", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder order (dedup-aware subtopic prompt beats custom prompt beats default), the warn-and-default type resolution, and the single role-collapse retry — each independently prevents a real port failure mode. Adapt the image block wording to your media pipeline; keep "exact markdown, reuse verbatim" or models will paraphrase URLs. Omit gpt-researcher's specific PromptFamily class table; keep the mapping-dict + default-fallback shape.
