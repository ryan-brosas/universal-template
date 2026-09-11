<!-- capsule-v2 -->
# tracking-dummy-uuid-privacy — How is per-subscriber tracking disabled without deleting code paths?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** What exactly changes when IndividualTracking or global DisableTracking flips?

## Dummy-UUID substitution lattice
**Path/Symbol:** template funcs `internal/manager/manager.go:TemplateFuncs` (:371-432, TrackLink :373-384, TrackView :385-402); dummy const `dummyUUID = "00000000-0000-0000-0000-000000000000"` (:39); link cache `trackLink` (:611-639); public handlers `cmd/public.go:LinkRedirect` (:554-587) and `RegisterCampaignView` (:589-617); analytics SQL `queries/campaigns.sql -- name: get-campaign-link-counts` (%s = COUNT(*) vs COUNT(DISTINCT subscriber_id)).
**Signature:** `TrackLink(url string, msg *CampaignMessage) string`; sub UUID chosen at render: real vs dummyUUID.
**Data Shape:** cfg flags `IndividualTracking bool`, `DisableTracking bool`; ViewTrackURL/LinkTrackURL are printf templates taking (campUUID, subUUID).

### Decisive source
```go
subUUID := msg.Subscriber.UUID
if !m.cfg.IndividualTracking {
	subUUID = dummyUUID
}
return m.trackLink(url, msg.Campaign.UUID, subUUID)
```

**Flow:** render time: tracking off globally ⇒ links stay raw + pixel omitted entirely; individual off ⇒ SAME URLs emitted but with the all-zero UUID for everyone. Click/view time: handler mirrors config — global-off resolves URL without recording (`GetLinkURL`) / returns pixel with Cache-Control no-cache without recording; individual-off records with empty sub UUID; previews excluded via `campUUID != dummyUUID && subUUID != dummyUUID` double-guard. Aggregation: unique-counts query interpolates `%s = *` when individual tracking is OFF because all rows would otherwise dedupe to one dummy subscriber.
**Invariant:** The privacy switch is a VALUE transformation applied consistently at render, ingest, AND aggregation — flipping IndividualTracking after sends exist silently mixes real and dummy UUIDs in link_clicks (counts remain correct only via the interpolated aggregate). trackLink failure fails OPEN to the original URL (never break the email over analytics).
**Probe:** `bash -c "cd <repo> && grep -rnF '00000000-0000-0000-0000-000000000000' internal/manager/manager.go cmd/public.go | wc -l"` → 1; `grep -nF 'pqErr.Column == \"campaign_id\"' internal/core/campaigns.go` (view-record unique-violation swallow → nil).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "TrackLink TrackView dummy", limit: 10 });
```
## Verdict
Adopt value-substitution over code-deletion for privacy toggles, plus fail-open analytics registration. Adapt UUID scheme freely. Omit the anti-spam pixel CSS recipe if you don't do open-tracking.
