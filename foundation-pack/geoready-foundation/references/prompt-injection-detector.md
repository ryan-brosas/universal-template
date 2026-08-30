<!-- capsule-v2 -->
# Prompt-injection detector — how do you catch 8 families of AI-manipulation content without drowning in false positives?

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** What severity ladder and per-category heuristics keep an injection scanner high-signal on real pages?

## Eight category detectors → counted categories → two-axis verdict
**Path/Symbol:** `src/geo_optimizer/core/injection_detector.py:audit_prompt_injection` (312–361), `_compute_severity` (364–404).
**Signature:** `audit_prompt_injection(soup, raw_html: str) -> PromptInjectionResult`.
**Data Shape:** per-category `(found: bool, count: int, samples: list[str]≤3 truncated to 150 chars)`; result adds `patterns_found` (active categories), `severity` ∈ {clean, suspicious, critical}, `risk_level` ∈ {none, low, medium, high}.

### Decisive source
```python
# Severity: direct LLM instructions or comment prompts are ALWAYS critical,
# regardless of count; otherwise it's the number of distinct CATEGORIES active
if result.llm_instruction_found or result.html_comment_injection_found:
    result.severity = "critical"
elif categories_active >= 3:
    result.severity = "critical"
elif categories_active >= 1:
    result.severity = "suspicious"

# aria-hidden false-positive guard (gap #4.16.3): a collapsed mobile menu is a long
# aria-hidden block BY DESIGN — nearly-all-link text reads as navigation, not cloaking
words = text.split()
if len(words) > 50 and not _is_mostly_link_text(el, len(words)):   # link-word ratio ≥0.8 ⇒ skip
    is_suspicious = True
```

**Flow:** categories run independently — CSS-hidden (`display:none|visibility:hidden|font-size:0|opacity:0` with ≥3 chars of text), invisible Unicode ≥5 matches (`\u200b-\u200f,\ufeff,\u202a-\u202e,\u2060`), LLM instruction regexes over RAW html (~20 patterns incl special tokens `<|system|>`, `[INST]`, Llama/Gemma headers, jailbreak phrases), HTML comments suspicious when >500 chars OR containing `prompt:/instruction:/system:/ai:/llm:` keywords OR matching an LLM pattern, monochrome (fg hex == bg hex after 3→6-digit normalize, or rgba alpha <0.05), micro-font (<2px after pt×1.33/em×16 conversion), data-attr `^data-(ai|prompt|llm|instruction|context|system)-`, aria-hidden as above.
**Invariant:** Detection runs on BOTH soup (DOM semantics) and raw html (comments/attributes BeautifulSoup may normalize); samples are bounded (max 3 × 150 chars) so hostile pages can't bloat reports; risk_level is orthogonal to severity — hidden-text alone is severity=suspicious but risk=medium.
**Probe:** `tests/test_prompt_injection.py::TestSeverityAndRisk::test_severity_critical_su_llm_instruction` (+ per-category suites; `PYTHONPATH=src pytest tests/test_prompt_injection.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "prompt injection severity categories", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the category-count severity ladder + navigation-shape exemption + sample bounding for any content-manipulation scanner; adapt pattern lists to current model special tokens; omit Italian keyword variants if your corpus is English-only.
