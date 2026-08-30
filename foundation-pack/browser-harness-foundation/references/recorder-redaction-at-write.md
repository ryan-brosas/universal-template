<!-- capsule-v2 -->
# Redaction at write time — how do you keep real secrets out of a folder people share?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** OAuth redirects and password fields would land real secrets in a shared recording — where and how are they scrubbed?

## URL param scrub + password masking at capture, plus a sensitive-regex safety net
**Path/Symbol:** `src/browser_harness/recorder.py:_scrub_url` (:52-53) with `_URL_SECRETS` (:44-49), `_mask` (:320-324), `_CTX_JS` (:58-67); `src/browser_harness/video.py:safe_text`/`safe_label` (:600-621) with `SENSITIVE` (:18-22).
**Signature:** `_scrub_url(url) -> str`; `_mask(text, ctx) -> str`; `safe_text(event) -> str|None`.
**Data Shape:** `_URL_SECRETS` matches `[?&#](code|access_token|id_token|refresh_token|token|assertion|client_secret|client_info|session_state|api_?key|sig|signature|auth|authorization|password|secret)=[^&#]+` (case-insensitive).

### Decisive source
```python
def _scrub_url(url):
    return _URL_SECRETS.sub(r"\1REDACTED", str(url))   # keep the KEY, redact value

def _mask(text, ctx):
    text = str(text)
    if ctx.get("input") == "password":
        return "•" * len(text)                          # mask at CAPTURE time
    return text[:_TEXT_LIMIT]                           # 500-char cap

# video.py safety net: even if a value slips through, never emit it
def safe_text(event):
    value = event.get("text")
    if value is None: return None
    if event.get("helper") in TYPE_HELPERS: return "<typed text hidden>"
    if event.get("input") == "password" or SENSITIVE.search(value):
        return "<sensitive>"
    return value[:120]
```

**Flow:** recorder scrubs `url`/`to` fields at write time (`_scrub_url`), masks password-field text at capture (`_mask`), then the video pipeline re-guards every emitted value with `safe_text`/`safe_label` (SENSITIVE regex + `<typed text hidden>`/`<sensitive>` placeholders + 120-char cap).
**Invariant:** redaction is GENERATION-TIME (at the write boundary), not a downstream afterthought; the URL scrub preserves the parameter name so structure survives while the secret is replaced; the video layer treats typed text as hidden by default and only reveals it via an explicit `showTyping` + source-line ledger.
**Probe:** no isolated unit test for the scrub regex (covered via recorder/video integration) — coverage caveat: verify `_URL_SECRETS` against your own auth-param names when porting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "_scrub_url _mask safe_text sensitive redact", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt generation-time redaction (URL-key-preserving scrub + password mask + sensitive-regex safety net) for any media/log pipeline; adapt the param list and regex; omit nothing. Coverage caveat: regex list needs review per host.
