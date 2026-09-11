<!-- capsule-v2 -->
# Citation marker resolution — bracket-family tolerance, code-span protection, and strip-not-fake on any provenance miss

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you rewrite the model's `[sN]` ledger citations into per-message display chips without corrupting code, silently eating format drift, or letting a citation point at evidence this turn didn't retrieve?

## resolve_citations + the drift canary
**Path/Symbol:** `src/cuga/backend/knowledge/sources.py` (`_MARKER_RE` :271; `_CODE_RE` :275-277; `_UNSUPPORTED_MARKER_RE` :285; `resolve_citations` :308-363; `_warn_unsupported_markers` :292-305; envelope stamping `annotate_envelope_with_citations` + `CITATION_DIRECTIVE` :366-410).
**Signature:** `resolve_citations(text: str, ledger: SourceLedger | None) -> (display_text, [snapshot dicts])`.
**Data Shape:** marker = `[sN]`, `[s1, s4]`, `[s1 s4]`, case-insensitive, across the SQUARE-BRACKET FAMILY: ASCII `[ ]`, fullwidth `［ ］`, lenticular `【 】`, tortoise-shell `〔 〕`. Resolution always rewrites to ASCII `[n]` so the frontend chip injector (which matches `[n]`) works regardless. Display numbers assigned by first appearance.

### Decisive source
```python
# :360-362 — odd parts are code, left BYTE-IDENTICAL
parts = _CODE_RE.split(text)
resolved = "".join(part if i % 2 else _MARKER_RE.sub(_sub, part) for i, part in enumerate(parts))

# _CODE_RE covers fenced blocks INCLUDING unterminated ones + inline spans:
r"(```[\s\S]*?```|~~~[\s\S]*?~~~|```[\s\S]*$|~~~[\s\S]*$|``[^`\n](?:[^`\n]|`[^`\n])*``|`[^`\n]*`)"

# :339-352 — two distinct strip reasons, logged separately for monitoring
this_turn = in_ledger and ... ledger.retrieved_this_turn(cite_id)
if not this_turn:
    reason = "not from this turn's retrieval" if in_ledger else "not in ledger"
```

**Flow:** warn once if a cite_id appears in an UNSUPPORTED style (`(s1)`, `{s1}`, `«s1»` … — silent drift must stay VISIBLE after the 【sN】 bug shipped unclickable citations; skipped inside code since `foo(s1)` is a call, not a citation) → no supported markers → return unchanged → split into code/non-code segments → rewrite markers only in prose: unknown ids strip, stale-turn ids strip with a different log reason, first-seen ids get `mark_cited` + next display number → snapshots ordered by display n.
**Invariant:** Strip-mode (ledger None: feature off / chit-chat) removes ALL markers SILENTLY — never warn per-marker or you mask real misses. A marker that cannot be tied to THIS turn's retrieval is stripped even when its record exists: "correct-and-uncited beats confidently wrong." Code segments (including TRUNCATED fences from cut-off LLM output) pass through byte-identical. The directive teaching the format rides ON the retrieval envelope at composition time (`CITATION_DIRECTIVE` appended to `reading_directive`), thousands of tokens closer than the system-prompt contract.
**Probe:** direct tests `tests/unit/test_citation_resolver.py::test_square_bracket_family_resolves_to_ascii` (:95 parametrized), `::test_unsupported_bracket_style_is_logged_not_silent` (:107), `::test_unsupported_marker_inside_code_is_not_warned` (:120), `::test_strip_mode_does_not_warn` (:129), `::test_real_ledger_miss_still_warns` (:141), `::test_unterminated_fence_protects_marker` (:153), `::test_double_backtick_inline_protects_marker` (:162), `::test_space_separated_marker_list` (:174), `::test_comma_list_expands_to_adjacent_numbers` (:48); E2E `tests/integration/test_knowledge_citation_e2e.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "resolve_citations _MARKER_RE _CODE_RE annotate_envelope_with_citations CITATION_DIRECTIVE", limit: 10 });
```

## Verdict
Adopt segment-split resolution with unterminated-fence protection, the four-bracket-family tolerance rewritten to canonical ASCII, separate strip-reason logging, and silent strip-mode. Adapt which bracket styles you tolerate (extend `_MARKER_RE` when your logs show new drift — that's the designed response). Omit nothing from the canary: making drift visible is what turned one bug class into a monitoring signal.
