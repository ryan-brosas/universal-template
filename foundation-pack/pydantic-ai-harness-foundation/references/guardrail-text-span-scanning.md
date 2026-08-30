<!-- capsule-v2 -->
# Text-span guardrail scanning: secrets split across content parts match nothing per-part

## Source / Question
`pydantic_ai_harness/guardrails/detectors.py` (+~188L drift) @ `main@f971198` — A `ToolReturn.content` may be a LIST of parts; the model reads adjacent text parts as ONE string, so a secret split across two parts (`sk-` in part 1, key body in part 2) matches nothing when detectors run per-part. How do you scan spans without breaking part metadata or CachePoint boundaries?

## Path / Symbol
`guardrails/detectors.py` — `for_tool_result_text()` machinery: `_detect_content_text` (verdict-or-replacement per text), `_carries_no_model_content` (CachePoint-only predicate), `_merge_span` (:boundary-preserving collapse), `_detect_text_run` (per-part THEN joined pass), `_detect_tool_result_content` (runs split on model-visible parts, trailing-None flush).

## Signature
```python
def _carries_no_model_content(part: UserContent) -> bool:
    return isinstance(part, CachePoint)   # THE only UserContent member that separates parts visually but not to the model
def _detect_text_run(detector, run) -> tuple[GuardrailResult | None, Sequence[UserContent], bool]
    # pass 1: every text part individually (originals kept for pass 2)
    # pass 2 (len(texts)>1): detector over ''.join(ORIGINALS)
```

## Data Shape
Runs accumulate str/TextContent AND CachePoint (visual separator, not semantic); any Image/Audio/Document/Video/Binary/UploadedFile part ENDS a run because each puts a payload between texts. Replacement keeps part shape via `dataclasses.replace(part, content=text)` preserving `TextContent.metadata`.

### Decisive source
Joined-pass anchoring hazard (:docstring): "Redacting a fragment can strip the very characters a pattern anchors on — `sk-` at the front of a key — which would leave the rest of the value exposed while the joined pass reported the span clean." Hence joined scan uses ORIGINALS, not per-part rewrites. Collapse decision: keep separate parts when their individual sanitization already equals whole-span sanitization ("boundaries carry nothing… each part keeps its own metadata"); differ ⇒ something reachable ONLY across a boundary exists ⇒ collapse to `_merge_span`. Marker-side rule in `_merge_span`: a CachePoint before the first / after the last text keeps its side ("moving it would change what the caller asked to be cached for nothing"); an INTERIOR marker has lost the split it marked and moves AHEAD of merged text, "which narrows the cached prefix rather than widening it". Single-text spans scanned ONCE (joined pass would agree with itself): "`TextDetector` is a public extension point, so a detector that is stateful or bills per call would otherwise see `content='x'` and `content=['x']` differently."

**Flow:** content list → split into maximal runs of (text ∪ CachePoint) parts → per-run: detect each part → terminal verdict short-circuits → join originals and detect again → equal? keep parts : collapse span → reassemble.
**Invariant:** no detector sees rewritten text in the joined pass; cache-marker sides stable; replacement preserves part type/metadata; non-text replacement from a text detector = loud UserError.

## Probe (direct test)
`tests/guardrails/test_detectors.py` — split-secret matrix (span-joining catches cross-part secret; per-part-only RED without it), CachePoint side-stability cases, single-part-no-double-scan case, metadata-preservation after replace. Suite green at HEAD (guardrails tests in the 977-passed battery).

## Retrieve
```
search_graph --project pydantic-ai-harness --name-pattern '_detect_text_run _merge_span _carries_no_model_content'
```

## Verdict
**Adopt** original-text joined-pass + boundary-preserving merge for ANY content-part redaction pipeline. **Adapt** run-splitting predicate if your stack adds new non-model-content markers. **Omit** nothing.
