<!-- capsule-v2 -->
# Recorder action-details projection — how do you record WHAT an agent did without recording the secrets it typed?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** How should an action recorder turn arbitrary helper calls (positional or keyword) into a minimal, privacy-scrubbed event dict?

## Per-helper whitelist projection + context-aware password masking
**Path/Symbol:** `src/browser_harness/recorder.py:_details` (:294-317), `_mask` (:320-324), consumed by `_capture` (:261-291); `_TEXT_LIMIT = 500` (:38).
**Signature:** `_details(helper: str, args: tuple, kwargs: dict, ctx: dict) -> dict`; inner resolver `arg(i, name, default=None)` = `args[i] if len(args) > i else kwargs.get(name, default)`.
**Data Shape:** ctx comes from the page-side `_CTX_JS` probe merged into the event before `_details` runs — `ctx["input"] == "password"` marks the focused element as a password field.

### Decisive source
```python
elif helper == "type_text":
    d["text"] = _mask(arg(0, "text", ""), ctx)
...
return {k: v for k, v in d.items() if v is not None}
```
```python
def _mask(text, ctx):
    if ctx.get("input") == "password":
        return "•" * len(text)
    return text[:_TEXT_LIMIT]
```

**Flow:** For each whitelisted helper name, project ONLY the named safe fields (click coordinates, scroll deltas+defaults, target URL, selector, key names); unknown helpers project nothing. Text-bearing fields (`type_text`, `fill_input`) pass through `_mask`: bullet-mask preserving length when the page context says password input, else truncate to 500 chars. `_capture` then scrubs `url`/`to` values, appends the screenshot frame name, and writes one NDJSON line — the whole observe path is never-raise.
**Invariant:** Recording is an ALLOWLIST of projected fields per known helper, never a dump of args — unknown helpers yield `{}` rather than leaking their arguments. Secrets are masked AT WRITE TIME (generation time), not at replay/review time, so the on-disk events file never contains the plaintext; masking preserves length (timing/shape stays reviewable). `None` values are dropped so absent optional args never appear as explicit nulls.
**Probe:** Executed against pinned source (pure function): positional `(120,80)` and kwargs `{x,y}` both → `{'x':120,'y':80}`; `type_text('hunter2')` with `{'input':'password'}` → `'•••••••'` (length preserved); 900-char text → exactly 500 chars; unknown helper `js` → `{}`; `goto_url(None)` → `{}` (None dropped). No direct unit test covers `_details` — coverage caveat; anchors verified at source :261-324.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "browser-harness", qualified_name: "browser-harness.src.browser_harness.recorder._details" });
```

## Verdict
Adopt allowlist-per-action projection, positional-or-keyword arg resolution for wrapper-tolerant logging, generation-time password masking with length preservation, and None-dropping. Adapt the field whitelist to your helper surface and the 500-char cap to your storage budget. Omit the JPEG frame-capture collision loop if your recorder has no screenshots.
