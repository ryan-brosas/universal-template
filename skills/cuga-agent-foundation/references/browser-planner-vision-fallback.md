<!-- capsule-v2 -->
# BrowserPlanner vision fallback — how does a singleton planner node survive vision-capable templates on vision-less endpoints?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Why must a blank 1×1 image be supplied even after vision is disabled, and how is a runtime vision rejection detected and recovered?

## Template-requires-img vs use-vision-effective split with rejection flip
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/browser/browser_planner_agent/browser_planner_agent.py:_BLANK_IMAGE` (:28-31), `_VISION_REJECTION_MARKERS` (:34-41), `_looks_like_vision_rejection` (:44-47), `BrowserPlannerAgent.__init__` (:50-71), `run` (:78-126).
**Signature:** `run(input_variables: AgentState) -> AIMessage`; constructor takes `use_vision_effective: bool = True` (build-time resolution: `settings…use_vision AND model_supports_vision(dyna_model)`).
**Data Shape:** `_BLANK_IMAGE` = 1×1 transparent PNG data URL; markers = lowercase substrings ("content must be a string", "image_url", "multimodal", "image input", "does not support images", "vision").

### Decisive source
```python
        # The prompt template bakes in the ``img`` slot at build time, so it
        # requires ``img`` on every invoke for the agent's whole lifetime — even
        # after a vision rejection flips ``use_vision_effective`` off ...
        self._template_requires_img = use_vision_effective
        ...
        except Exception as exc:
            if not image_attached or not _looks_like_vision_rejection(exc):
                raise
            self.use_vision_effective = False
            data["use_vision"] = False
            data["img"] = _BLANK_IMAGE      # popping would re-raise missing variables {'img'}
            return await self.chain.ainvoke(data)
```
plus the atomic last-image snapshot:
```python
            try:
                last_image = tracker.images[-1]
            except (AttributeError, IndexError, TypeError):
                last_image = None
```

**Flow:** build time resolves effective vision; template bakes `{% if use_vision %}` img slot accordingly. Each run: attach tracker's last screenshot (atomic snapshot vs collect_image race), else blank placeholder IF template requires img; on invoke failure WITH an image attached AND marker-match ⇒ flip instance flag off, set use_vision=False, retry text-only with blank img. Subsequent runs keep supplying blank img because `_template_requires_img` stays true forever.
**Invariant:** Two independent booleans: template shape (fixed at build) vs runtime capability (flippable) — conflating them causes either `missing variables {'img'}` crashes or silently dropped screenshots. Rejection heuristic only fires when an image was actually attached, so unrelated failures still raise. The snapshot try/except IS the race guard against the unlocked singleton tracker.
**Probe:** Direct test `tests/unit/test_browser_planner_missing_img.py` — five cases incl. `test_vision_rejection_retries_with_blank_img_then_stays_safe` (:86) asserting two chain calls, `use_vision=False`, and persistent blank-img safety.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_BLANK_IMAGE _looks_like_vision_rejection use_vision_effective BrowserPlannerAgent", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the build-time/runtime vision split, marker-based rejection detection gated on attachment, and permanent blank-slot satisfaction for baked templates. Adapt marker lists to your endpoint error dialects. Omit hybrid-mode variable summaries if you have no API/browser hybrid.
