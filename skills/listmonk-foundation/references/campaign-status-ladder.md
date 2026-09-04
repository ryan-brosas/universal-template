<!-- capsule-v2 -->
# campaign-status-transition-ladder — Which status transitions are legal and where is the ladder enforced?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** What guards separate draft→scheduled→running→paused→finished→cancelled?

## App-layer guard ladder over DB rows
**Path/Symbol:** `internal/core/campaigns.go:UpdateCampaignStatus` (:250-310) — five-case switch :258-284; statuses const in `models/campaigns.go`; automatic transitions written by manager cleanup (`internal/manager/pipe.go:192-244`) and next-campaigns SQL claim.
**Signature:** `func (c *Core) UpdateCampaignStatus(id int, status string) (models.Campaign, error)`.
**Data Shape:** draft | scheduled | running | paused | finished | cancelled (+ scheduled requires SendAt valid).

### Decisive source
```go
switch status {
case models.CampaignStatusDraft:
	if cm.Status != models.CampaignStatusScheduled { errMsg = ...onlyScheduledAsDraft }
case models.CampaignStatusScheduled:
	if cm.Status != Draft && cm.Status != Paused { errMsg = onlyDraftAsScheduled }
	if !cm.SendAt.Valid { errMsg = needsSendAt }
case models.CampaignStatusRunning:
	if cm.Status != Paused && cm.Status != Draft { errMsg = onlyPausedDraft }
case models.CampaignStatusPaused:
	if cm.Status != models.CampaignStatusRunning { errMsg = onlyActivePause }
case models.CampaignStatusCancelled:
	if cm.Status != Running && cm.Status != Paused { errMsg = onlyActiveCancel }
}
if len(errMsg) > 0 { return Campaign{}, echo.NewHTTPError(400, errMsg) }
res := c.q.UpdateCampaignStatus.Exec(cm.ID, status)
if n, _ := res.RowsAffected(); n == 0 { return ..., 400 notFound }
```

**Flow:** fetch current row FIRST (guard evaluates against DB truth, not caller belief) → validate requested transition against the ladder → exec update → RowsAffected==0 ⇒ 404-style badRequest (row vanished mid-flight) → return updated model. Automatic writers BYPASS the ladder deliberately: pipe.cleanup sets finished/paused based on drain outcome; next-campaigns CTE claims scheduled→running when time elapses; unknown messenger at pipe creation force-cancels (`newPipe` → UpdateCampaignStatus(cancelled)).
**Invariant:** Manual API changes go through the ladder; system transitions don't — porters adding validation in SQL or triggers will deadlock the dispatcher's own claims. DeleteCampaign/DeleteCampaigns also verify RowsAffected for not-found parity.
**Probe:** `bash -c "cd <repo> && awk '/func \(c \*Core\) UpdateCampaignStatus/,/^}/' internal/core/campaigns.go | grep -c 'case models.CampaignStatus'"` → 5; `grep -c 'res.RowsAffected(); n == 0' internal/core/campaigns.go` → 2 (status + delete).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "UpdateCampaignStatus paused", limit: 10 });
```
## Verdict
Adopt explicit transition ladders validated against freshly-read state with RowsAffected confirmation. Adapt error taxonomy to your framework. Omit i18n keys.
