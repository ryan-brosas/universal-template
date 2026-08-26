<!-- capsule-v2 -->
# send-learning-truncation-ladder — How does telemetry survive oversized payloads without killing the run?

**Source:** gpt-engineer MIT `main@a90fcd543eedcc0ff2c34561bc0785d2ba83c47e`; Codebase Memory `gpt-engineer`. **Question:** What is the exact failure ladder between extract_learning and the network, and which exceptions can still escape?

## Truncation-ladder seam
**Path/Symbol:** `gpt_engineer/applications/cli/collect.py:collect_learnings` (:65-124) + `send_learning` (:37-62); caller `collect_and_send_human_review` (:141-177).
**Signature:** `send_learning(learning: Learning) -> None`; `collect_learnings(prompt, model, temperature, config: any, memory: DiskMemory, review: Review) -> None`.
**Data Shape:** RudderStack `track(user_id=learning.session, event="learning", properties=learning.to_dict())`; size budget 32<<10 bytes measured on `learnings.to_json().encode("utf-8")`.

### Decisive source
```python
try:
    send_learning(learnings)
except RuntimeError:                                  # rudderstack oversize signal ONLY
    max_size = 32 << 10
    current_size = len(learnings.to_json().encode("utf-8"))
    overflow = current_size - max_size
    remove_length = overflow + len(f"[REMOVED {overflow} CHARACTERS]") + 100
    learnings.logs = (
        learnings.logs[:-remove_length]
        + f"\n\n[REMOVED {remove_length} CHARACTERS]"
    )
    print("WARNING: learning too big, removing some parts. ...")
    try:
        send_learning(learnings)
    except RuntimeError:
        print("Sending learnings crashed despite truncation. Progressing without saving learnings.")
```

**Flow:** extract → attempt send → RuntimeError? ⇒ compute byte overflow vs 32KiB → truncate that many chars (+marker length+100 safety) OFF THE TAIL of `logs` only → append `[REMOVED n CHARACTERS]` marker → warn → retry once → second RuntimeError swallowed with a progress-anyway message.
**Invariant:** (1) Only `RuntimeError` triggers truncation and only it is ever caught — any other exception from `send_learning` propagates into `collect_and_send_human_review`, which has NO try/except, i.e. a non-RuntimeError telemetry bug would crash the generate tail after successful codegen. (2) The lazy `import rudderstack.analytics` inside `send_learning` keeps telemetry optional at import time; write_key/dataPlaneUrl are hardcoded constants (:55-56). (3) The marker reports `remove_length` (margin-inflated), not the true overflow — off-by-design, harmless for analytics but do not reuse the arithmetic as an exact-size claim. (4) Truncation mutates ONLY `logs`; prompt/model/review always ship whole. (5) Failure posture is fail-open: worst case is lost telemetry, never lost user work — preserve this ordering when porting.
**Probe:** no direct upstream test exists for collect.py (grep of tests/ shows none; coverage check confirms tests live only for learning/main planes) — deterministic source-pin probe: `grep -n 'max_size = 32 << 10' gpt_engineer/applications/cli/collect.py` → :102.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "collect_learnings send_learning RuntimeError max_size REMOVED truncation", limit: 10 });
```

## Verdict
Adopt the two-attempt tail-truncation ladder with fail-open semantics and exception-type narrowness (RuntimeError-only) made explicit in your port; adapt endpoint/write-key to your telemetry plane; omit RudderStack entirely if you have another sink — keep the oversize-budget concept. Caveat recorded honestly: zero direct upstream tests for this seam; all evidence is source-read plus graph retrieval.
