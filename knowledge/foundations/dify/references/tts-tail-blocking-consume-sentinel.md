<!-- capsule-v2 -->
# tts-tail-blocking-consume-sentinel — Why did the TTS autoplay tail stop polling on a wall-clock timeout?

**Source:** dify Apache-2.0 `main@44aec257`; Codebase Memory `ext-dify`. **Question:** After the text stream ends, how does the pipeline drain remaining synthesized audio completely — without a fixed timeout that truncates slow generations? (Rewritten by #41043; the old loop spun on `TTS_AUTO_PLAY_TIMEOUT` and could cut audio off.)

## publish(None) end-of-text sentinel + blocking queue drain to terminal status
**Path/Symbol:** `api/core/app/apps/advanced_chat/generate_task_pipeline.py:_wrapper_process_stream_response` (:359-409) + `_listen_audio_msg` (:347-357); workflow twin `api/core/app/apps/workflow/generate_task_pipeline.py` (:256-end, `publish(None)` :288); producer `api/core/base/tts/app_generator_tts_publisher.py:AppGeneratorTTSPublisher._runtime` + `check_and_get_audio(*, block)` (:148-160) + `cancel()` (:56-60).
**Signature:** generator `_wrapper_process_stream_response(trace_manager=None)` yields audio/text/error frames; `check_and_get_audio(block: bool = False) -> AudioTrunk | None`.
**Data Shape:** `AudioTrunk(status, audio, audio_type, error)` — status ∈ {`responding`, `finish`, `error`}; `publish(None)` means "text is complete" (the runtime then flushes its residual buffer as one final TTS request and breaks); `cancel()` sets a threading.Event and enqueues None so the runtime thread wakes and exits. TTS publisher creation is now GATED on `self._base_task_pipeline.stream` — non-streaming responses never synthesize audio.

### Decisive source
```python
tts_publisher.publish(None)                      # text done → flush residual sentence
while True:
    audio_trunk = tts_publisher.check_and_get_audio(block=True)
    assert audio_trunk is not None
    if audio_trunk.status == "responding":
        yield MessageAudioStreamResponse(audio=..., audio_type=..., task_id=task_id)
        continue
    if audio_trunk.status not in {"finish", "error"}:
        raise RuntimeError(f"TTS publisher returned an unknown status: {audio_trunk.status}")
    yield MessageAudioEndStreamResponse(audio="", task_id=task_id)
    if audio_trunk.status == "error":
        ...yield ErrorStreamResponse(err=audio_trunk.error, ...)
    return
```
Mid-stream listener (same file): `while audio_response := self._listen_audio_msg(...)` forwards `responding` chunks as they arrive, treats `finish`/`error` as nothing-to-forward, and RAISES RuntimeError on any other status (`_listen_audio_msg`, executed at the pin).

**Flow:** stream phase interleaves text frames with non-blocking audio polls → on ErrorStreamResponse: cancel publisher + emit empty audio-end frame + yield the error (no tail drain after failure) → normal completion: publish(None) sentinel → BLOCKING consume until terminal trunk → finish ⇒ audio-end frame only; error ⇒ audio-end + ErrorStreamResponse carrying the producer's exception → `finally: cancel()` guarantees the daemon runtime thread dies even when the consumer aborts mid-stream.
**Invariant:** COMPLETION IS SIGNAL-DRIVEN, NOT TIME-DRIVEN — the old wall-clock `TTS_AUTO_PLAY_TIMEOUT` poll loop is gone; termination requires an explicit terminal trunk, so slow synthesis drains fully but a wedged producer would block forever (accepted trade: the runtime thread always emits exactly one terminal trunk via try/except); unknown statuses fail LOUDLY (RuntimeError names the status) instead of being silently dropped as before; error trunks MUST carry `.error` (None raises "terminal without an exception").
**Probe:** `cd api && .venv/bin/pytest -p no:cacheprovider -o addopts= tests/unit_tests/core/app/apps/workflow/test_generate_task_pipeline_core.py -q` → 47 passed (pipeline-core suite covers wrapper/stream/tail behavior incl. the new gating). EXECUTED GREEN at `44aec257`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "_wrapper_process_stream_response check_and_get_audio publish None", limit: 10 });
```

## Verdict
Adopt sentinel-plus-blocking-drain shutdown for any producer/consumer audio-or-chunk pipeline: it removes arbitrary deadlines and makes every terminal state explicit. Adapt the trunk/status vocabulary and the cancellation event. Omit the streaming-only gate if your app synthesizes unconditionally. Direct coverage via the pipeline-core suite (47 green); the advanced-chat twin shares the shape.
