<!-- capsule-v2 -->
# Output-blob validation taxonomy — which recorded-blob defects are hard failures and which are life?

**Source:** screenity GPL-3.0 `master@e10e375fafa1680de99ca6db36536dd4a1f4f7d4`; Codebase Memory `screenity`. **Question:** After a recording finalizes, what distinguishes "the encoder is broken" from "the take is just small" from "validation itself timed out" — without ever punishing a good take?

## Demux-based validation with three-tier verdict
**Path/Symbol:** `src/media/fastRecorderGate.ts:826-936` (`validateFastRecorderOutputBlob`); consumer `src/pages/Recorder/Recorder.jsx:2100-2185` (onFinalized validation block).
**Signature:** `validateFastRecorderOutputBlob(blob: Blob | null, opts?: {minBytes?, timeoutMs?, videoCodec?, audioCodec?, recordingId?}): Promise<FastRecorderValidationResult>` where the result is `{ok, hardFail, reasons, details}`.
**Data Shape:** mediabunny demux under a 2s default `Promise.race`; reasons array; `hardFail` boolean computed AFTER filtering informational reasons.

### Decisive source
```ts
  if (!blob) { reasons.push("no-blob"); return { ok:false, hardFail:true, ... }; }
  ...
  if (blob.size < minBytes) { reasons.push("blob-too-small"); }
  ...
    const tracks = await Promise.race([
      demuxInput.getTracks(),
      new Promise((_, reject) => setTimeout(() => reject(new Error("demuxer-timeout")), demuxTimeoutMs)),
    ]);
    ...
    if (videoTracks.length === 0) { reasons.push("demuxer-no-video-track"); }
  ...
  // blob-too-small is informational: a short clip is legitimately tiny (~15KB).
  // The empty-encoder case surfaces as demuxer-no-video-track, not size.
  const defectReasons = reasons.filter((r) => r !== "blob-too-small");
  const hardFail =
    defectReasons.includes("no-blob") ||
    defectReasons.includes("unexpected-mime") ||
    defectReasons.includes("demuxer-no-video-track");
```
Consumer-side inconclusive tier:
```ts
                // Timeout means slow reassembly (multi-GB take in a throttled
                // tab), not a bad recording, and it already shipped. Mark it
                // inconclusive so it neither fails the take nor penalizes fast.
                validation = {
                  ok: false,
                  hardFail: !isRebuildTimeout,
                  inconclusive: isRebuildTimeout,
                  reasons: [isRebuildTimeout ? "rebuild-timeout" : "validation-exception"],
                  details: { error: String(err) },
                };
```

**Flow:** null/size/mime quick checks → lazy-load mediabunny (~3 MB deferred import) → bounded demux → track census (counts, codecs, dimensions into details) → filter informational reasons → compute hardFail → persist verdict to storage; consumer marks start/done diag events so "validator never finished" is observable as start-without-done.
**Invariant:** size alone must never fail a take; only no-blob / unexpected-mime / zero-video-tracks are device-defect-grade (`hardFail` feeds `markFastRecorderFailure("validation-failed", …)`); a rebuild or demux timeout yields an explicit inconclusive verdict that neither fails the user's take nor penalizes the fast recorder.
**Probe:** deterministic anchors: grep for `a short clip is legitimately tiny` (:911-912), `neither fails the take nor penalizes fast` (:2132-2134), `the unwritten-verdict case in field reports` (:2091-2092). Byte-exact at HEAD.

## Get live surrounding code
**Retrieve:**
```
trace_path(project="screenity", function_name="validateFastRecorderOutputBlob", direction="inbound")
→ observed callers_total=2: Recorder.Recorder.onFinalized :2118 and Region.Recorder.onFinalized —
  both WebCodecs finalize paths validate off the critical path after video-ready shipped.
```

## Verdict
Adopt the reason-taxonomy + hardFail/inconclusive separation and the bracketing diag markers. Adapt the demuxer choice (mediabunny replaced a `<video>`+seek+rVFC pipeline that stacked ~3-4s timeouts). Omit the specific storage keys for persisted verdicts.
