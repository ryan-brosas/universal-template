<!-- capsule-v2 -->
# Session-start admission & sampling — how does the ingest edge decide who gets recorded, and what exactly rides back to the tracker?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** Where is sampling enforced (dice roll), how do condition rates override project sample rate, and which response fields drive client behavior?

## startSessionHandlerWeb admission funnel
**Path/Symbol:** `backend/pkg/sessions/api/web/handlers.go:startSessionHandlerWeb` (:104-291), `validateTrackerVersion` (:85-101), `recordSession`/`modifyResponse` (`model.go:47/:51`), `StartSessionRequest/Response` (`model.go:5-45`).
**Signature:** `func (e *handlersImpl) startSessionHandlerWeb(w http.ResponseWriter, r *http.Request)`; request JSON `{projectKey, token, timestamp, doNotRecord, bufferDiff, isOffline, condition, trackerVersion, ...}`.
**Data Shape:** `p.SampleRate byte (0-100)` from project row; response carries `token, sessionID, startTimestamp, delay, beaconSizeLimit, compressionThreshold, canvasEnabled/Quality/FPS, protocolVersion`.

### Decisive source
```go
if err := validateTrackerVersion(req.TrackerVersion); err != nil { ... 428 UpgradeRequired ... }
p, err := e.projects.GetProjectByKey(*req.ProjectKey)      // 404 if unknown/inactive
if !p.IsWeb() { ... 403 ... }
ua := e.uaParser.ParseFromHTTPRequest(r)                   // 403 on unparseable UA
...
tokenData, err := e.tokenizer.Parse(req.Token)
if err != nil || req.Reset {                               // NEW session path
    dice := byte(rand.Intn(100))
    if req.Condition != "" {
        rate, err := e.conditions.GetRate(p.ProjectID, req.Condition, int(p.SampleRate))
        if err == nil { p.SampleRate = byte(rate) }         // condition rate overrides
    }
    if dice >= p.SampleRate {
        ... http.StatusForbidden "capture rate miss" ...    // sampled OUT
    }
```

**Flow:** version gate (semver ≥6.0.0, `-beta` suffixes stripped before parse; fail = 428 so trackers auto-upgrade) → project lookup by key → platform + UA gates → geoIP enrich → token parse DECIDES new-vs-resume: unparsable/reset rolls the dice under condition-or-project sample rate, miss = plain 403 (tracker treats as silent no-record) → new sessions compose flake-ID sessionID where the ID ENCODES its own timestamp (`ExtractTimestamp(tokenData.ID)` returns it later) → recordSession (¬doNotRecord) writes a Postgres row AND produces SessionStart to Kafka topic → beaconSizeCache.Add(sessionID, p.BeaconSize) pre-seeds the per-session size limit → response includes everything the client needs in ONE round-trip.
**Invariant:** Sampling happens ONLY at new-session time — a resumed session never re-rolls, so capture decisions are stable for the whole session. The dice comparison is `dice >= SampleRate` with `rand.Intn(100)` ∈ [0,99]: rate=100 records always, rate=0 never. doNotRecord=true still mints a token (for flags/conditions fetch) but skips DB+Kafka writes entirely — that's the cold-start conditional-fetch contract.
**Probe:** `grep -n 'dice >= p.SampleRate' backend/pkg/sessions/api/web/handlers.go` from repo root → line 184; `grep -n '>=6.0.0' backend/pkg/sessions/api/web/handlers.go` → line 86 (verified live). Coverage caveat: handler has no direct Go test at pin; pinned by source anchors + compile.
**Retrieve:** search_graph project openreplay query "startSessionHandlerWeb pushMessagesHandlerWeb beacon" → rank-1 Methods `startSessionHandlerWeb :104-291`, `pushMessagesHandlerWeb :300-415`, `NewBeaconCache :19-27` line-exact.

## Verdict
Adopt new-session-only sampling with condition-rate override, semver version gate returning 428, and one-shot response envelope as pure admission behavior; adapt UA parsing/geoIP to your providers; omit Kafka/Postgres write specifics behind your own persistence ports.
