<!-- capsule-v2 -->
# Video-brief validation — how do you turn a human-authored edit brief into a verified composition without trusting a single field?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** A brief drives video generation — how is every field validated so a bad brief fails loudly instead of producing a subtly-wrong video?

## reject-unknown everywhere + typed validators + source-hash pinning + budget gate
**Path/Symbol:** `src/browser_harness/video.py:compile_brief` (:473-614), `reject_unknown` (:176-180), `validate_narration_cadence` (:307-336), `duration_budget` (:280-292), `write_source_manifest`/`verify_source_manifest` (:146-174), `validate_privacy` (:419-471).
**Signature:** `compile_brief(summary, brief, style, revealed_text=None) -> composition`; raises `BriefError` on any violation.
**Data Shape:** brief keys (task/summary/plan/outcomes/actions/privacy/explanations/outcomeTitle/outcomeSummary); narration ≤7 words; plan 2-5 items; outcomes 1-5; actions ≥1.

### Decisive source
```python
def reject_unknown(value, allowed, where):
    unknown = sorted(set(value) - allowed)
    if unknown: raise BriefError(f"{where} has unsupported field(s): {', '.join(unknown)}")

# narration cadence: sticky, not mirrored
for segment in segments:
    cues = [b for b in segment if b.get("narration")]
    if len(segment) >= 3 and len(cues) > math.ceil(len(segment) / 2):
        raise BriefError("narration is sticky: set it only when the thought changes ...")
    consecutive = 0
    for beat in segment:
        consecutive = consecutive + 1 if beat.get("narration") else 0
        if consecutive >= 3: raise BriefError("three consecutive actions change narration ...")

# hard budget: compiled video that exceeds house style is an ERROR, not a warning
if duration > budget + 0.001:
    raise BriefError(f"compiled video is {duration:.1f}s; house-style budget is {budget:.1f}s ...")
```

**Flow:** reject unknown keys → validate task/plan/outcomes/actions → resolve viewport from the first action's frame event → build intro/action/explanation/outcome beats with computed durations → enforce narration cadence → add raw-to-card holds → compute budget → REJECT if over → validate privacy (reviewed frames must cover used frames; redact rects finite/positive/opaque-hex) → emit `window.COMPOSITION = {...}`.
**Invariant:** unknown keys are ERRORS (the contract stays deliberately small); narration is sticky (max ceil(n/2) cues per segment, never 3 consecutive); viewport must match within ±2px; source files are sha256-pinned at `init` so ANY post-init change is rejected; the duration budget is a hard gate.
**Probe:** no standalone test file for video.py at this HEAD (video is exercised via CLI) — coverage caveat: validation behavior verified by direct source read; the cadence/budget functions are pure and deterministic.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "compile_brief reject_unknown narration cadence budget", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt reject-unknown + typed validators + source-hash pinning + hard budget for any generative-media pipeline; adapt key sets and pacing constants; omit nothing. Coverage caveat: no upstream unit test for video.py.
