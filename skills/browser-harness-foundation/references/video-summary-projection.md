<!-- capsule-v2 -->
# Sanitizing summary projection — how does a raw event log become an LLM-readable summary that cannot leak secrets even though it re-derives every line?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** A recording's events.jsonl holds raw typed text, URLs and titles — how is the agent-facing summary built so secrets are destroyed by default while still letting a brief reference exactly one original event?

## sourceLine-keyed projection with deny-by-default text
**Path/Symbol:** `src/browser_harness/video.py:init_recording` (:661-713), `safe_text` (:642-651), `safe_label` (:654-658), `load_revealed_text` (:622-639); consumed by `compile_action` showTyping gate (:409-418).
**Signature:** `init_recording(recording, require_explicit=False) -> int`; `load_revealed_text(events_path) -> dict[int, str]`; `safe_text(event) -> str | None`.
**Data Shape:** summary events carry {frame, sourceLine, helper, ts, route:"Browser", tab, viewport:{w,h}, cursor:{x,y}|None, box, text, textLength, password}; `sourceLine` = 1-based line number in events.jsonl; `revealed_text` maps sourceLine → original typed string ONLY for non-password type-helper events.

### Decisive source
```python
def safe_text(event):
    value = event.get("text")
    if value is None:
        return None
    if event.get("helper") in TYPE_HELPERS:      # type_text/fill/fill_input
        return "<typed text hidden>"             # ALL typed text hidden...
    value = str(value)
    if event.get("input") == "password" or SENSITIVE.search(value):
        return "<sensitive>"                     # ...unless explicitly revealed
    return value[:120]

# load_revealed_text: the ONE key back to reality
if event.get("helper") in TYPE_HELPERS and event.get("input") != "password":
    revealed[source_line] = str(text)
```
And the consumer-side join (`compile_action`):
```python
source_line = event.get("sourceLine")
if show_typing and source_line not in revealed_text:
    raise BriefError(f"actions[{index}].showTyping requires the original typed event")
beat["type"] = {
    "box": {...},
    "text": revealed_text[source_line] if show_typing else "••••••",
    **({} if show_typing else {"redact": True}),
}
```

**Flow:** init parses events.jsonl line-by-line → each framed event projected through `safe_text` (typed ⇒ `<typed text hidden>`; password OR SENSITIVE-regex hit ⇒ `<sensitive>`; else truncated to 120) with the RAW length kept separately in `textLength` → writes recording-summary.json → `write_source_manifest` pins hashes. Later, `load_revealed_text` re-reads events.jsonl and records sourceLine→text ONLY for non-password typing events; a brief may flip typing visible ONLY at an action whose event number resolves to a sourceLine present in that ledger.
**Invariant:** the summary NEVER contains raw typed text — reveal is an explicit, auditable second channel keyed by `sourceLine`, not a flag on the summary row; password-typed text has no reveal path AT ALL (excluded from the ledger before any brief can ask); SENSITIVE regex (emails/@, tenant|user|object ids, bare UUIDs) destroys identity-looking values even outside passwords; `route` is hardcoded "Browser" so navigation targets never enter the summary either; textLength preserves utility (a brief can reason about input size) without content.
**Probe:** no dedicated unit suite for video.py at this pin — coverage caveat recorded; deterministic anchors verified at source :635-638 (ledger excludes password), :26-28 (hidden/sensitive placeholders), :409-413 (brief-side refusal when sourceLine absent from ledger). The refusal branch is exercised structurally because summaries written without a matching events.jsonl fail manifest verification.
**Coverage caveat:** upstream tests exercise this only via CLI integration; porters should unit-test `safe_text`/`load_revealed_text` directly (both pure).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "init_recording safe_text load_revealed_text sourceLine", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the two-channel design (sanitized projection + sourceLine-keyed reveal ledger) whenever an LLM consumes a log derived from sensitive captures; adapt TYPE_HELPERS/SENSITIVE to your helpers. Omit textLength if consumers don't need it.
