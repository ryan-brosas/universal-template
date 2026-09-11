<!-- capsule-v2 -->
# Unicode stream decoding — what does `iter_content(decode_unicode=True)` actually yield, and how does replay slicing work?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `requests`. **Question:** How are streamed bytes decoded to text mid-stream without splitting multibyte characters, and what happens when the body was already consumed?

## utils.stream_decode_response_unicode / utils.iter_slices + iter_content wiring
**Path/Symbol:** `src/requests/utils.py:stream_decode_response_unicode` (:594-610), `.iter_slices` (:621-630); call site `src/requests/models.py:Response.iter_content` (:958-977).
**Signature:** `stream_decode_response_unicode(iterator, r) -> Generator[str | bytes]`; `iter_slices(string, slice_length) -> Generator[bytes | str]`.
**Data Shape:** wraps the byte-chunk generator from `generate()` OR the replay generator over memoized `_content`; output chunks are str when decoding is active, otherwise the original bytes.

### Decisive source
```python
def stream_decode_response_unicode(iterator, r):
    if r.encoding is None:
        yield from iterator            # bytes pass through UNDECODED
        return

    decoder = codecs.getincrementaldecoder(r.encoding)(errors="replace")
    for chunk in iterator:
        rv = decoder.decode(chunk)
        if rv:
            yield rv
    rv = decoder.decode(b"", final=True)
    if rv:
        yield rv                       # flush buffered partial character

# iter_content tail:
if self._content_consumed:
    content = cast(bytes, self._content)
    chunks = iter_slices(content, chunk_size)   # replay = re-slice memoized bytes
else:
    chunks = generate()
if decode_unicode:
    chunks = stream_decode_response_unicode(chunks, self)
```

**Flow:** iter_content picks a live-stream generator or an iter_slices replay over `_content` → the unicode wrapper decorates EITHER path → encoding None yields raw bytes (so `decode_unicode=True` does NOT guarantee str!) → otherwise an incremental decoder with errors="replace" converts chunk-by-chunk, buffering incomplete multibyte sequences across chunk borders and flushing them with a final empty decode.
**Invariant:** The incremental decoder — not naive `chunk.decode()` — is what keeps multibyte characters split across TCP chunks intact; replacing it with per-chunk decoding corrupts UTF-8 streams. `iter_slices` treats slice_length None or <= 0 as "whole string in one slice" (never an infinite loop). Replay works only because `_content` holds bytes even when consumers asked for unicode.
**Probe:** Direct tests: `tests/test_requests.py::test_response_decode_unicode` (:1468-1485, asserts all-str chunks on BOTH the pre-consumed replay arm and the io.BytesIO streaming arm), `tests/test_utils.py::test_iter_slices` (:658-674, parametrized incl. negative-length→single-slice).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "requests", query: "stream_decode_response_unicode iter_slices", limit: 10 });
```

## Verdict
Adopt incremental-decoder wrapping with final-flush and the None-encoding bytes pass-through (document it loudly). Adapt the encoding source (`r.encoding`) to host charset resolution. Omit chardet/charset_normalizer selection — response-content-plane already scopes that to host policy.
