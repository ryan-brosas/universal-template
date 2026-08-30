<!-- capsule-v2 -->
# tts-audio-mime-validation-ladder — How does TTS audio reach the browser with a MIME type nobody can lie about?

**Source:** dify Apache-2.0 `main@44aec257`; Codebase Memory `ext-dify`. **Question:** Three independent sources of "what format is this audio" (model schema metadata, per-chunk provider claims, the bytes themselves) disagree — which wins, and when is the mismatch fatal? (Rewritten by #41043: previously chunks carried no type at all and players guessed.)

## Magic-byte sniffing + claim validation feeding one resolved stream MIME
**Path/Symbol:** `api/core/base/tts/audio_mime.py` — `normalize_audio_mime_type` (:42-49), `get_model_audio_mime_type` (:51-61), `sniff_audio_mime_type` (:63-81), `_normalize_reported_mime_type` (:84-91), `_extract_audio_chunk` (:94-102), `resolve_audio_mime_type` (:105-139), `inspect_audio_stream` (:142-end); consumer/publisher state machine `api/core/base/tts/app_generator_tts_publisher.py:AppGeneratorTTSPublisher._runtime` (:66-146).
**Signature:** `resolve_audio_mime_type(audio, *, declared_mime_type=None, reported_mime_type=None) -> str`; `inspect_audio_stream(audio_stream, declared_mime_type=None) -> tuple[Generator[bytes], str]`.
**Data Shape:** Alias table `_AUDIO_MIME_TYPE_ALIASES` (:18-40) maps ~20 spellings → 7 canonical browser MIME types; unknown/unsupported ⇒ `InvokeBadRequestError`, never silent passthrough. Sniffer reads a 32-byte signature (`_SIGNATURE_SIZE`) and returns None (not mp3) on ID3-only headers; MP3 vs AAC disambiguated by second-byte bit masks (`& 0xF6 == 0xF0` sync-word vs `& 0xE0`). Precedence: reported (chunk) > declared (schema) > sniffed > default `audio/mpeg`.

### Decisive source
```python
expected_mime_type = normalized_reported_mime_type or normalized_declared_mime_type
if expected_mime_type and detected_mime_type and expected_mime_type != detected_mime_type:
    raise InvokeBadRequestError(
        "TTS provider output MIME does not match its audio bytes: "
        f"declared {expected_mime_type}, detected {detected_mime_type}"
    )
...
return normalized_reported_mime_type or detected_mime_type or normalized_declared_mime_type \
    or DEFAULT_TTS_AUDIO_MIME_TYPE   # (verbatim ladder spans :122-138)
```
Publisher side (`_runtime`): `inspect_audio_stream(invoke_result, self._declared_audio_mime_type)` validates EVERY response; an incremental mid-sentence request is only legal while the resolved type is still the declared default — `next_audio_type != DEFAULT_TTS_AUDIO_MIME_TYPE` under `incremental_request` raises "cannot be played incrementally"; a BETWEEN-response change raises "changed MIME type between audio responses".

**Flow:** schema read at publisher init (failure-tolerant debug-log → None) → each TTS invocation's stream is peeked chunk-by-chunk until 32 signature bytes accumulate (leading chunks BUFFERED, never dropped) → claims validated against magic bytes → resolved type stamped onto every `AudioTrunk("responding", audio=base64..., audio_type=...)` → consumers forward `audio_type` verbatim to the client.
**Invariant:** MISMATCH IS FATAL, not corrected — a provider claiming X while emitting Y-bytes raises rather than being silently rewritten (the browser must not be told a wrong type); within ONE response all chunks must agree and across responses of one run the resolved type must stay stable (both raise); sniffing alone is advisory (returns None for opaque codecs like bare mp3 frames after ID3), so claims are REQUIRED to be honest — that is exactly what the ladder enforces; `inspect_audio_stream` preserves prefix bytes so validated playback is byte-complete.
**Probe:** `cd api && .venv/bin/pytest -p no:cacheprovider -o addopts= tests/unit_tests/core/base/tts/test_audio_mime.py -q` → 7 passed (prefix preservation, mismatch rejection, unsupported reported type, declared-fallback, plugin-metadata normalization, mp3-vs-adts signatures, ID3-not-proof). EXECUTED GREEN at `44aec257`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "sniff_audio_mime_type resolve_audio_mime_type inspect_audio_stream", limit: 10 });
```

## Verdict
Adopt the three-source precedence ladder with fatal-mismatch semantics whenever untrusted producers emit typed binary streams. Adapt the canonical type table and the signature probes to your codec set. Omit the TTSAudioChunk compatibility carrier if your runtime already emits bytes. Direct tests cover all seven behaviors; no coverage caveat.
