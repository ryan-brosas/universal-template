<!-- capsule-v2 -->
# consent-file-latch — How is telemetry consent persisted, and what does declining actually do?

**Source:** gpt-engineer MIT `main@a90fcd543eedcc0ff2c34561bc0785d2ba83c47e`; Codebase Memory `gpt-engineer`. **Question:** What are the exact read/write semantics of the `.gpte_consent` latch across runs?

## Consent-latch seam
**Path/Symbol:** `gpt_engineer/applications/cli/learning.py:check_collection_consent` (:183-198) + `ask_collection_consent` (:201-234).
**Signature:** `check_collection_consent() -> bool`; `ask_collection_consent() -> bool`.
**Data Shape:** state file `./.gpte_consent` (CWD-relative, NOT home/global) containing exactly `"true"` when opted in; absent or any other content = undecided.

### Decisive source
```python
def check_collection_consent() -> bool:
    path = Path(".gpte_consent")
    if path.exists() and path.read_text() == "true":
        return True
    else:
        return ask_collection_consent()

# ask_collection_consent "n" branch: prints refusal message and
#     return False        # <-- NO write_text anywhere on the decline path
```

**Flow:** every review request → check file → exists∧content=="true" (exact match; no strip) ⇒ silent True → otherwise interactive y/n loop (`answer.lower()` accepted, prompt repeats until y|n) → "y" writes `"true"` to the file, thanks + prints delete-file opt-out hint, returns True → "n" prints refusal, returns False **without touching the file**.
**Invariant:** (1) Declining is NEVER persisted — the next run re-asks from scratch (pinned by an explicit test asserting `not Path(".gpte_consent").exists()` after decline). Only explicit "yes" is durable. (2) Consent scope = current working directory: running from another directory silently resets to undecided. (3) Exact-string comparison means trailing whitespace/newline in the file forces a re-ask — write side always emits bare `"true"` so round-trips hold. (4) The opt-out mechanism for a consenting user is manual file deletion (the UI says so). (5) Graph caveat: `trace_path` shows an extra inbound edge `collect.collect_and_send_human_review → check_collection_consent`, but the source has exactly ONE call site (`learning.human_review_input:134`); trust the source.
**Probe:** `tests/applications/cli/test_collection_consent.py` — real-filesystem matrix with `cleanup` fixture unlinking `.gpte_consent`: exists+"true"⇒True :33-35; exists+"false"+input"n"⇒False :38-41; missing+yes⇒file created=="true" :44-48; missing+no⇒file ABSENT :51-54; invalid-then-yes/no re-prompt pairs :91-103.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "check_collection_consent ask_collection_consent gpte_consent true", limit: 10 });
```

## Verdict
Adopt the one-way durable-consent latch (only yes persists; decline re-prompts next run); adapt the marker file location per host (make it global if your port wants cross-project memory — that is a behavior CHANGE, decide deliberately); omit RudderStack specifics. Direct real-fs tests pin all eight scenarios at pin.
