<!-- capsule-v2 -->
# Auxiliary write fail-open contract — what happens when introduction, conclusion, draft titles, or URL summaries fail?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** When porting the report-assembly helpers, how must each auxiliary LLM call degrade on failure so the overall report still assembles?

## Uniform try/log/return-empty across the four auxiliary writers
**Path/Symbol:** `gpt_researcher/actions/report_generation.py:12-60` (`write_report_introduction`), `:63-112` (`write_conclusion`), `:115-157` (`summarize_url`), `:160-206` (`generate_draft_section_titles`).
**Signature:** all four take `(query|url, context|content, role/agent_role_prompt, config, websocket=None, cost_callback=None, **kwargs)` and return `str` — except `generate_draft_section_titles` which returns `List[str]`.
**Data Shape:** every call is `create_chat_completion(model=config.smart_llm_model, temperature=0.25, stream=True, max_tokens=config.smart_token_limit, cost_callback=cost_callback)`; failure shape is the empty value of the return type, never an exception.

### Decisive source
```python
# report_generation.py:58-60 (identical shape at :110-112, :155-157, :204-206)
    except Exception as e:
        logger.error(f"Error in generating report introduction: {e}")
return ""
```
```python
# report_generation.py:197, 203 — two quirks in generate_draft_section_titles only:
            websocket=None,          # caller's websocket param is IGNORED — titles never stream
...
        return section_titles.split("\n")   # no blank-line filtering
```

**Flow:** each auxiliary call wraps its single `create_chat_completion` in try/except → logs with a function-specific message → returns "" (or [] for titles). The report assembler then concatenates possibly-empty parts: DetailedReport builds `f"{introduction}\n\n{toc}\n\n{report_body}\n\n{conclusion_with_references}"` (detailed_report.py:202), so a failed intro/conclusion yields an empty segment, not a crash.
**Invariant:** auxiliary sections must degrade to the empty value of their return type and NEVER raise — the final report is assembled from parts that may individually be empty, and one failed conclusion must not discard a fully written body. The final report call is the exception to this contract: it has its own collapse retry (see report-prompt-ladder-collapse-retry) and only then gives up with "". QUIRK to know, not necessarily copy: draft titles hardcode `websocket=None`, so they are the one auxiliary call that can never stream; and `summarize_url` is exported from `actions/__init__.py` but has ZERO internal callers at this pin — it is public library surface, so its contract is part of the API even though the repo never exercises it.
**Probe:** byte anchors verified at pin: report_generation.py:58-60 / :110-112 / :155-157 / :204-206 (four identical except-log-return tails), :197 (websocket=None), :203 (split); grep confirms `summarize_url` appears only in actions/__init__.py exports + its own def (no callers). Coverage caveat: NO upstream test pins any of the four auxiliary writers — probe is source-read only; runner BLOCKED in-lane (missing aiofiles, read-only checkout).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-researcher", query: "write_report_introduction write_conclusion summarize_url generate_draft_section_titles", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the uniform fail-open empty-value contract for every non-critical LLM call in a multi-part document pipeline — it is what lets assembly continue past partial failures. Adapt log messages to your logger; keep them function-specific (they are the only diagnostic when a section silently vanishes). Omit the websocket=None quirk unless you also want unstreamed titles; keep summarize_url-style orphan helpers out of your API surface unless external users need them.
