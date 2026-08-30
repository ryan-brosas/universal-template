<!-- capsule-v2 -->
# Line-padded exact replace — 100-newline moat that makes "append to file" a plain substring match

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How do you express "add these lines at the end" through the SAME exact-substring machinery as a mid-file edit, without a separate code path?

## Pad, match, unpad
**Path/Symbol:** `aider/coders/search_replace.py`: `line_padding = 100` (:246), `line_pad(text)` (:249), `line_unpad(text)` (:254).
**Signature:** `line_pad(text) -> "\n"*100 + text + "\n"*100`; `line_unpad(text) -> str | None`.
**Data Shape:** the empty search text becomes unique inside the padded original (the only place 100 consecutive newlines occur is the padding itself), so appending reduces to rung-1 `search_and_replace` on padded texts.

### Decisive source
```python
def line_unpad(text):
    if set(text[:line_padding] + text[-line_padding:]) != set("\n"):
        return          # padding violated ⇒ refuse (caller sees None = failed rung)
    return text[line_padding:-line_padding]
```

**Flow:** caller pads all three texts → strategies run unchanged → successful result is unpadded before use; any strategy output whose head/tail isn't pure newlines fails the check and the ladder moves on.
**Invariant:** unpad REFUSES rather than strips when the 100-newline moat is damaged — content containing ≥100 blank lines in a row collides with the sentinel, so the guard must stay; pad constant must be identical across pad/unpad call sites.
**Probe:** executed this run: `.pi/work/foundations-deep-farm/scratch-aider-pass2/probe_gate5.py::mdstream-window-math` (asserts pad→unpad identity AND that non-blank padding returns None); no upstream direct tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", name_pattern: "line_unpad", limit: 5 });
```

## Verdict
Adopt the sentinel-moat trick whenever one generic matcher must cover appends/creations; adapt the pad width to your matcher's uniqueness needs; omit nothing else — it's 12 load-bearing lines. Coverage caveat: no upstream tests; probe-executed.
