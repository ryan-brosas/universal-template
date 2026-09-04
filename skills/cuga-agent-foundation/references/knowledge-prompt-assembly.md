<!-- capsule-v2 -->
# Knowledge prompt assembly — ordered composition, the citations-prompt-must-lie-never rule, and behavioral prompt engineering

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you assemble contract + doc list + adaptation + base instructions into one system-prompt section such that instruction-following is maximized and the prompt NEVER promises a behavior the runtime won't perform?

## The single seam: assemble_system_prompt_section
**Path/Symbol:** `src/cuga/backend/knowledge/awareness.py` (`assemble_system_prompt_section` :435-542 returning dataclass `AssembledKnowledgePrompt` :410-432; `compose_knowledge_prompt` :60-79; `_render_client_adaptation_block` :175-215; cross-scope gate in `get_knowledge_summary` :299-307; recency tail :346-358; legacy-section surgical regex :518-524).
**Signature:** `assemble_system_prompt_section(engine, agent_id, thread_id, base_instructions="", *, agent_config_hash=None, search_config=None) -> AssembledKnowledgePrompt(text, prompt_hash, knowledge_block_chars, contract_chars, has_knowledge)`.
**Data Shape:** disabled/empty paths return `text=base_instructions`, zeroed counters, `has_knowledge=False`; enabled returns composed text + 12-hex sha256 audit hash computed IDENTICALLY across cuga_lite and chat_agent (an asymmetry would hide drift on one path).

### Decisive source
```python
# :60-79 — order = contract, THEN doc list, THEN base; empty chunks skipped
# so no double-blank runs some LLMs treat as content boundaries
for chunk in (contract_text, doc_list_block, base_instructions):
    if chunk:
        stripped = chunk.strip("\n")
        if stripped: parts.append(stripped)
return "\n\n".join(parts)

# :506-513 — the prompt may not lie: use resolution's OWN predicate
# Session-aware: a per-thread override disables citations even when the
# agent config leaves them on. Use the SAME predicate resolution uses ...
if citations_enabled_for(cfg, thread_id):   # else markers would be stripped post-hoc
    contract_text += "\n" + CITATIONS_CONTRACT

# :199-207 — MANDATORY framing beats advisory framing (measured on mid-tier models)
"<client_adaptation priority=\"high\">",
"**MANDATORY operator rules for this deployment.** Apply these rules on EVERY response..."
```

**Flow:** engine None or config disabled → pass-through with hash of base only → resolve collections → build doc summary (agent docs permanent / session docs temporary with LIVE-pointer anchored inside the session section) → load canonical contract from markdown with `{{max_search_attempts}}` substituted (missing file → "" silently; budget fallback 3) → if citations on: surgically DELETE the legacy "## Citing sources" prose section by regex and append `[sN]` CITATIONS_CONTRACT (non-match fine — operators edit that file) → compose ordered → log hash+len never text (PII/prompt-IP) → profile addendum → pre-response verification tail when adaptation present.
**Invariant:** Prompt/behavior symmetry is the core invariant: any instruction the prompt gives must be checkable by the same predicate enforcement uses. Adaptation block renders a structural sentinel `<client_adaptation>none</client_adaptation>` when empty so prompt SHAPE stays stable for A/B diffs. Behavioral findings are encoded as structure: XML-tagged spans weighted higher than markdown headers; "MANDATORY … EVERY response" framing measurably raised compliance after advisory phrasing was silently dropped in production; forced verbalization ("name the strongest candidate on EACH side") converts an unforced scan into a commit step; the recency tail phrases checks BEFORE responding to trigger self-review at output time.
**Probe:** direct tests `tests/unit/test_knowledge_client_adaptation.py` + `tests/integration/test_knowledge_integration.py` (compose/adaptation surfaces); `tests/unit/test_server_citation_egress.py::test_rehydration_honors_session_override_over_agent_flag` (:159 — rehydration must gate on the SAME session-aware predicate as stamping and resolution, else a restart re-issues colliding cite_ids) + `tests/unit/test_citation_settings.py` enablement ladder (:45-132). Coverage caveat: `compose_knowledge_prompt` ordering and cross-scope-commit gate verified by source read + integration tests, no dedicated unit test pins the exact order.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "assemble_system_prompt_section compose_knowledge_prompt get_knowledge_summary client_adaptation CITATIONS_CONTRACT", limit: 10 });
```

## Verdict
Adopt the ordered composition with empty-chunk skipping, the single-seam dataclass return (fields extend without breaking callers), prompt-hash audit parity across consumers, and above all the shared-predicate citations rule. Adapt section wording, the adaptation tag name, and addendum sourcing to your deployment. Omit the CRM-era doc-list copy unless you have equivalent scope semantics.
