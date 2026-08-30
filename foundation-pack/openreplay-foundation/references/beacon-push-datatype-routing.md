<!-- capsule-v2 -->
# Beacon push handler & DataType routing — how does one ingest endpoint accept compressed multi-stream batches and route them to the right Kafka topics without dropping expired-token data?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** How is the per-session beacon size limit enforced server-side, how do player/assets/devtools/analytics streams split across topics, and why does an expired token still get its last batch written?

## pushMessagesHandlerWeb
**Path/Symbol:** `backend/pkg/sessions/api/web/handlers.go:pushMessagesHandlerWeb` (:300-415); size limit source `e.beaconSizeCache` (`beacon-cache.go:19-49`).
**Signature:** `func (e *handlersImpl) pushMessagesHandlerWeb(w http.ResponseWriter, r *http.Request)`; reads headers `DataType`, query `batch=<pageNo>_<batchNum>` and `split`.
**Data Shape:** Body may be gzip (client sets `Content-Encoding: gzip`); `DataType ∈ {player|assets|devtools|analytics|visual|""→"all"}`; topics `TopicRawWeb` vs `TopicRawAssets`; `tokenJustExpired bool`.

### Decisive source
```go
sessionData, err := e.tokenizer.ParseFromHTTPRequest(r)
tokenJustExpired := false
if err != nil {
    if errors.Is(err, token.JUST_EXPIRED) { tokenJustExpired = true }
    else { ... 401 ... return }                       // hard-expired/forged → reject
}
...
bodyBytes, err := api.ReadCompressedBody(e.log, w, r, e.beaconSizeCache.Get(sessionData.ID))
if err != nil {
    errCode := http.StatusRequestEntityTooLarge
    if tokenJustExpired { errCode = http.StatusUnauthorized }   // expired wins status race
...
} else {                                              // topic switch by DataType header
    topic := e.cfg.TopicRawWeb
    switch batchType {
    case "assets": topic = e.cfg.TopicRawAssets
    default:       // "analytics", "devtools", "replay"
        topic = e.cfg.TopicRawWeb
    }
    err = e.producer.Produce(topic, sessionData.ID, bodyBytes)
```

**Flow:** parse token from Authorization → JUST_EXPIRED latches a flag instead of failing → look up projectID for context → read+decompress body with the PER-SESSION beaconSizeCache limit (seeded at start from project config; 413 on exceed, or 401 if also just-expired) → "visual" batches carry a `split` byte offset validated `0 < split < bodySize` and are cut into player[:split] + assets[split:] two-topic writes (legacy single-request dual-stream format) → otherwise whole-body Produce by DataType → ALWAYS respond 401 after a successful just-expired write so the client restarts.
**Invariant:** Write-then-401 ordering is the contract: the batch IS durably produced before the client learns the token died — combined with QueueSender's grace window this makes expiry boundary lossless. The size limit is per-SESSION state on the server (not a constant), because beacon limits are project-configurable and can change between sessions. The visual/split path exists so old trackers that multiplexed two streams in one body still land bytes in the right topics; validation rejects split==0 and split>=bodySize as malformed rather than producing empty frames.
**Probe:** `grep -c 'tokenJustExpired' backend/pkg/sessions/api/web/handlers.go` from repo root → **7**; `grep -n 'split <= 0 || split >= bodySize' backend/pkg/sessions/api/web/handlers.go` → line 367 (verified live). Coverage caveat: no direct Go test at pin; pinned by source anchors + compile.
**Retrieve:** search_graph project openreplay query "pushMessagesHandlerWeb beacon DataType" → rank-1 Method `pkg.sessions.api.web.pushMessagesHandlerWeb :300-415` line-exact.

## Verdict
Adopt write-then-flag-expiry, per-session size cache enforcement, and header-keyed topic routing as pure ingest behavior; adapt Kafka producer + compression handling to your queue; omit the legacy visual/split multiplexing unless you must accept old tracker bodies.
