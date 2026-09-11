<!-- capsule-v2 -->
# Video action-beat compilation — which checks must run PER-ACTION at compile time so privacy and watchability cannot be violated downstream?

**Source:** browser-harness MIT `main@6bb1c847fd62638554618e8d1e03247b935ff9cf`; Codebase Memory `browser-harness`. **Question:** Given an already-validated brief plus the recording's event list, what does each action owe the beat sheet — and which refusals must happen here because no later stage can repair them?

## Per-action validation ladder → beat projection
**Path/Symbol:** `src/browser_harness/video.py`: `compile_action` (:339-435); helpers `event_at` (:226-234), `event_target` (:237-247), `require_matching_viewport` (:250-258); constants `ROUTE_UNSAFE`/`ACTION_KEYS`/`TYPE_HELPERS`/`CLICK_HELPERS`/`VIEWPORT_TOLERANCE` (:23-27, :56-69, :90-93).

**Signature:** `def compile_action(action, index, events, plan, first_ts, previous_target, viewport, pacing, revealed_text) -> tuple[dict, dict | None]`.

**Data Shape:** input action is a dict restricted to `ACTION_KEYS`; output beat carries `frame/route/chapter` plus optional `after/afterRoute/narration/label/detour/error/wide/cursor+click/type/cameraCut/t/dur`; returns the new focus target for the next action's continuity check.

### Decisive source
```python
    helper = str(event.get("helper") or "")
    cursor = event.get("cursor")
    if helper in CLICK_HELPERS:
        if not isinstance(cursor, dict) or cursor.get("x") is None or cursor.get("y") is None:
            raise BriefError(f"actions[{index}] identifies a click without captured coordinates")
        beat["cursor"] = {"x": cursor["x"], "y": cursor["y"]}
        beat["click"] = True
    elif helper in TYPE_HELPERS:
        box = event.get("box")
        if not isinstance(box, dict) or not all(box.get(key) is not None for key in ("x", "y", "w", "h")):
            raise BriefError(f"actions[{index}] identifies typing without a captured box")
        show_typing = action.get("showTyping") is True
        if show_typing and event.get("password"):
            raise BriefError(f"actions[{index}].showTyping cannot reveal a password field")
        source_line = event.get("sourceLine")
        if show_typing and source_line not in revealed_text:
            raise BriefError(f"actions[{index}].showTyping requires the original typed event")
        beat["type"] = {
            "box": {key: box[key] for key in ("x", "y", "w", "h")},
            "text": revealed_text[source_line] if show_typing else "••••••",
            **({} if show_typing else {"redact": True}),
        }
```

**Flow:** per action: type-check → `reject_unknown(ACTION_KEYS)` → bool-only `showTyping` → one-based `event_at` lookup (rejects out-of-range and frame-less events) → `require_matching_viewport` against the brief's viewport (±`VIEWPORT_TOLERANCE = 2`px; different-viewpoint recordings must be split or normalized) → chapter must index plan → route text banned from raw URLs/identity by `ROUTE_UNSAFE` (`@`, `[?#]`, `://`, tenant/user/object-id words, bare UUIDs) → optional afterEvent repeats event+viewport checks with its own semantic-route ban. Projection: click beats demand captured coordinates; typing beats demand a full box, refuse to reveal password fields even when asked, and only emit real text when `showTyping` AND the typed event exists in the reveal ledger — otherwise `"••••••"` + `redact: True`. Camera: `event_target` prefers cursor else derives box point `(x+0.3w, y+h/2)`; a jump over 0.58× viewport diagonal sets `cameraCut`. Timing: `t` is normalized `max(0, ts - first_ts)` rounded to 3; duration comes from the pacing budget.

**Invariant:** Refusals are compile-time and total: an invalid composition is *unrenderable*, never silently degraded (pairs with video-render-preflight-ladder). Privacy cannot be violated downstream because reveal paths are gated here at the data level (ledger membership), not by renderer discipline. Continuity target threading (`previous_target` in, new target out) makes camera decisions local per action.

**Probe:** Deterministic probes against pinned source (lane precedent; video module has no direct unit suite): bool-typed `showTyping` rejection exact message; box→(x+0.3w, y+h/2) derivation; `password×showTyping` refusal message byte-exact; masked positive control emits `redact: True`; `ROUTE_UNSAFE.search("https://x")` truthy vs semantic route falsy; cameraCut fires only beyond 0.58·diagonal with t-normalization verified.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "browser-harness", qualified_name: "browser-harness.src.browser_harness.video.compile_action" });
```
Returns :339-435 whole-method (verified live this pass; video.py untouched by the pin advance so pass-6 line ranges still hold).

## Verdict
Adopt per-action reject-unknown + typed refusal vocabulary + ledger-gated text reveal + derived-target camera-cut threshold; adapt the helper-name sets (`TYPE_HELPERS`/`CLICK_HELPERS`), tolerance constant, and house pacing numbers; omit the specific regex vocabulary of identity leakage unless porting the same threat model. Cross-bounds: reveal-ledger join owned by video-summary-projection; durations/holds owned by video-cadence-budget-gates; template-side camera safety owned by video-click-safe-camera. Coverage caveat: no direct upstream suite for video.py internals — deterministic probes substitute.
