<!-- capsule-v2 -->
# Loop detection detectors — how does a sliding window of hashed tool calls distinguish stuck loops from legitimate repetition?

**Source:** praisonai MIT `main@d82364ec23a83fd9a6e2e849a5285442b4734ca3`; Codebase Memory `praisonai`. **Question:** How is "the agent is stuck" computed from a bounded history of (tool, args) calls — which hash makes identical calls comparable, and how do the three detectors split responsibility so legitimate polling and alternating work are not flagged?

## agent/loop_detection.py detect_tool_loop
**Path/Symbol:** `src/praisonai-agents/praisonaiagents/agent/loop_detection.py` — `LoopDetectionConfig` (lines 37–62), `_stable_json` (lines 90–105), `hash_tool_call` (lines 109–121), `detect_tool_loop` (lines 312–410).
**Signature:** `detect_tool_loop(history: List[ToolCallRecord], tool_name: str, args: Any, config: Optional[LoopDetectionConfig] = None) -> LoopDetectionResult`; `hash_tool_call(tool_name, args) -> str` (16-char hex). Config defaults: `enabled=False` (opt-in), `history_size=30`, `warn_threshold=10`, `critical_threshold=20`, all three detectors on; `__post_init__` auto-corrects `critical <= warn` to `warn + 1`.

### Decisive source
```python
def hash_tool_call(tool_name: str, args: Any) -> str:
    stable = _stable_json({"t": tool_name, "a": args})
    return _sha256_hex(stable)   # sha256 hexdigest[:16]

def detect_tool_loop(history, tool_name, args, config=None):
    if config is None or not config.enabled:
        return _NOT_STUCK        # disabled → singleton safe result
    args_hash = hash_tool_call(tool_name, args)
    detectors = config.detectors or {}
    warn = config.warn_threshold
    critical = config.critical_threshold

    # --- poll_no_progress detector ---
    if detectors.get("poll_no_progress", True) and _known_poll_tool(tool_name):
        streak = _no_progress_streak(history, args_hash, tool_name)
        if streak >= critical:  return LoopDetectionResult(stuck=True, level="critical", detector="poll_no_progress", ...)
        if streak >= warn:      return LoopDetectionResult(stuck=True, level="warning", detector="poll_no_progress", ...)

    # --- ping_pong detector ---
    if detectors.get("ping_pong", True):
        pp_count = _ping_pong_streak(history, args_hash)
        ...  # same warn/critical ladder

    # --- generic_repeat detector ---
    if detectors.get("generic_repeat", True) and not _known_poll_tool(tool_name):
        count = _count_generic_repeat(history, args_hash, tool_name)
        ...  # same warn/critical ladder
    return _NOT_STUCK
```

**Flow:** disabled config short-circuits to the shared `_NOT_STUCK` singleton (zero allocation on the hot path) → canonicalize the current call via `_stable_json` (sorted dict keys, list/tuple recursion, `str()` fallback for non-serializable values) + sha256 truncated to 16 hex chars → run detectors in fixed order, each returning at most one result: (1) `poll_no_progress` applies ONLY to known poll tools and counts streaks of identical args AND identical result hashes (a poll that keeps getting new data is making progress); (2) `ping_pong` counts an alternating two-call oscillation pattern; (3) `generic_repeat` counts identical-args repeats but is SUPPRESSED for known poll tools (repeated polling with the same args is legitimate until results stop changing) → each detector has its own warn→critical level ladder with distinct remediation messages ("Increase wait time or report failure" vs "Stop ping-pong and try a different approach" vs "Execution blocked").
**Invariant:** detection is keyed on the canonicalized (tool, args) hash, so argument order and non-serializable objects cannot defeat it; the two poll-aware exclusions are complementary — poll tools escape generic_repeat but are judged by result-stagnation instead, non-poll tools never get poll leniency; thresholds are self-healing (`critical` can never be ≤ `warn`); every stuck result carries `detector`, `level`, `count`, and a human message naming the tool.
**Probe:** `tests/unit/test_loop_detection.py:107–184` pins the ladder end-to-end — disabled config with 50 identical recorded calls still returns `stuck is False`; with `warn=5/critical=10`: 4 repeats not stuck, 5th returns `level=="warning"` + `detector=="generic_repeat"`, 10th returns `level=="critical"`; six calls with *different* args never false-positive; results expose a `count` field and the tool name in the message.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "praisonai", query: "tool loop detection hash sliding window detector", name_pattern: "^detect_tool_loop$|^hash_tool_call$|^_no_progress_streak$", limit: 10 });
```

## Verdict
Adopt the canonicalized-hash sliding window plus the complementary poll-tool exclusion pair (generic_repeat suppressed for pollers, poll_no_progress requiring identical *results*) — that pair is what separates "legitimate long poll" from "stuck". Adopt the opt-in default (`enabled=False`) and the threshold auto-correction. Adapt the known-poll-tool list to your host's tool vocabulary and the 16-char hash truncation to your collision tolerance. Omit praisonai's OpenClaw port lineage and logger formatting. Coverage: no recorded index issue on cited paths; the detector ladder is directly tested including the disabled and no-false-positive cases.
