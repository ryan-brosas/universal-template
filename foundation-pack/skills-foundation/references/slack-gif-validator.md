<!-- capsule-v2 -->
# Slack GIF Validator — which dimension/size gates decide a GIF is Slack-ready, and how do emoji vs message rules differ?

**Source:** anthropics/skills (Apache-2.0) `main@3b3fad96`; Codebase Memory `mnt-hdd-utopia-inspo-reference-skills`. **Question:** What are the exact acceptance predicates, and what metadata does the validator return alongside the verdict?

## Squareness-for-emoji vs aspect+size-band-for-messages
**Path/Symbol:** `skills/slack-gif-creator/core/validators.py::validate_gif` (:11–118) + `is_slack_ready` (:121–136).
**Signature:** `validate_gif(gif_path, is_emoji=True, verbose=True) -> tuple[bool, dict]`; `is_slack_ready(...) -> bool` thin wrapper.
**Data Shape:** results dict carries `{file, passes, width, height, size_kb, size_mb, frame_count, duration_seconds, fps, is_emoji, optimal}`. Frame count via seek-until-EOFError; fps from `img.info["duration"]` × frames (default 100ms when absent).

### Decisive source
```python
if is_emoji:
    optimal = width == height == 128
    acceptable = width == height and 64 <= width <= 128
    dim_pass = acceptable            # square 64..128; 128x128 flagged 'optimal'
else:
    aspect_ratio = max(width, height) / min(width, height)
    dim_pass = aspect_ratio <= 2.0 and 320 <= min(width, height) <= 640
```

**Flow:** stat file → open with PIL → count frames by seeking to EOFError → derive duration/fps → branch emoji-vs-message predicate → return (verdict, full telemetry dict) with advisory prints (>5MB "consider fewer frames/colors").
**Invariant:** Emoji rule is SQUARENESS-first (any non-square fails regardless of resolution; 128×128 labeled optimal but 64–128 accepted), while message GIFs get an ASPECT band (≤2:1) plus a min-edge window (320–640px) — the two modes share NO predicate, so porters must not unify them. The verdict returned covers DIMENSIONS only; size is advisory telemetry, never a gate — the caller decides what "ready" means beyond geometry.
**Probe:** No upstream tests. Deterministic probes (anchors re-derived & executed 2026-08-24): `grep -c '64 <= width <= 128' skills/slack-gif-creator/core/validators.py` = 1; `grep -c 'aspect_ratio <= 2.0' skills/slack-gif-creator/core/validators.py` = 1.
**Coverage caveat:** platform thresholds are upstream's best knowledge at this pin; re-verify against Slack docs when porting.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-reference-skills", query: "validate_gif", limit: 5 });
// skills.skills.slack-gif-creator.core.validators.validate_gif Function validators.py 11-118
```

## Verdict
Adopt as the shape for platform-conformance validators: mode-split predicates, rich telemetry dict beside a boolean, advisory-not-gating for soft limits. Adapt thresholds per platform; keep emoji-squareness and message-aspect semantics separate.
