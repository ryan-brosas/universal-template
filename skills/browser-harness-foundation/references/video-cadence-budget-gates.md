<!-- capsule-v2 -->
# Narration-cadence + duration-budget compile gates — why is "narrate every step" an ERROR in a generated screencast, and how is pacing computed instead?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** When an LLM authors narration and durations for a beat-based video, what structural gates keep the output watchable without hand-tuning?

## sticky-narration segments + word-count pacing + hard budget
**Path/Symbol:** `src/browser_harness/video.py:validate_narration_cadence` (:307-336), `default_action_duration` (:261-277), `card_duration` (:198-207), `add_raw_to_card_holds` (:295-304), `duration_budget` (:280-292), enforced at `compile_brief` tail (:580-591).
**Signature:** `validate_narration_cadence(beats) -> None` (raises BriefError); `duration_budget(action_count, explanation_count, raw_to_card_count, pacing) -> float`.
**Data Shape:** beats carry optional `narration` (≤7 words, validated earlier); cards (`card: true`) split segments; pacing constants live in HOUSE_STYLE: captionBaseSeconds 0.35, captionSecondsPerWord 0.2, rawToCardHoldSeconds 0.55, baseDurationBudget 22, extraActionSeconds 1.25 per action past 5, extraExplanationSeconds 3 per explanation past 1, maximumDurationBudget 32.

### Decisive source
```python
# cadence: narration is STICKY — set it only when the thought changes
for segment in segments:
    cues = [beat for beat in segment if beat.get("narration")]
    if len(segment) >= 3 and len(cues) > math.ceil(len(segment) / 2):
        raise BriefError(
            "narration is sticky: set it only when the thought changes, then "
            "omit it while 2–3 screenshots advance underneath")
    consecutive = 0
    for beat in segment:
        consecutive = consecutive + 1 if beat.get("narration") else 0
        if consecutive >= 3:
            raise BriefError(
                "three consecutive actions change narration; omit narration on "
                "intervening actions so text and screenshots use different pacing")

# budget: COMPUTED from counts against a capped allowance — then HARD-enforced
budget = baseDurationBudget
budget += max(0, action_count - 5) * extraActionSeconds
budget += max(0, explanation_count - 1) * extraExplanationSeconds
budget += raw_to_card_count * rawToCardHoldSeconds      # each raw→card cut gets a hold
...
if duration > budget + 0.001:
    raise BriefError(f"compiled video is {duration:.1f}s; house-style budget is {budget:.1f}s. ...")
```

**Flow:** after all beats are built → segment by card boundaries → enforce two cadence rules (≤⌈n/2⌉ narrated beats per ≥3-beat segment; never 3 consecutive narrations) → walk consecutive beat pairs inserting `endStateHold` on every beat whose NEXT beat is a card (raw-to-card transition pause) → compute budget from counts → sum actual durations → exceed budget ⇒ REFUSE compilation with copy-editing instructions in the error text.
**Invariant:** narration mirroring every frame is a validation ERROR, not a style preference — text and screenshots are forced onto different rhythms; durations are never free-form numbers in the brief but COMPUTED from content (word counts at readingWpm=380, beat kinds, typing length ×0.035s) plus deterministic holds; the budget scales with task complexity (extras per action/explanation) but is absolutely capped at 32s — long videos must be split, not stretched; error messages teach the fix ("shorten card copy, remove redundant actions...") because the author is an agent.
**Probe:** no dedicated unit suite for video.py at this pin — coverage caveat recorded; both functions are pure/deterministic: anchors verified at source :307-336 (segment walk + two raises), :295-304 (hold insertion mutates dur BEFORE budget check), :286-292 (budget formula), :585-591 (sum vs budget with 1ms tolerance). The sibling capsule video-brief-validation carries the same cadence excerpt within its broader flow.
**Coverage caveat:** upstream tests exercise this via CLI integration only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "narration cadence duration_budget endStateHold", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt computed-pacing + hard-budget + cadence-as-error for any generated presentation/media pipeline driven by LLM specs; adapt constants to your medium. Omit the camera-cut heuristic if you have no virtual camera (it lives in compile_action, not here).
