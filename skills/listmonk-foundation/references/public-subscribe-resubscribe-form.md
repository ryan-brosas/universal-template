<!-- capsule-v2 -->
# public-subscribe-resubscribe-form — What does the unauthenticated subscription endpoint guarantee?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** How does a public form create-or-resubscribe without leaking private lists?

## Private-list gate then insert-or-reattach
**Path/Symbol:** `cmd/public.go:processSubForm` (:726-808), `PublicSubscription` (:536-549); private-list check `core.GetListTypes` (`internal/core/lists.go:126-147`); prefs/unsub pages `SubscriptionPage` (:199-253), `SubscriptionPrefs` (:255-347).
**Signature:** `func (a *App) processSubForm(c echo.Context) (bool, error)` — returns hasOptin.
**Data Shape:** form fields name/email/l[] (list UUIDs only — no numeric IDs on the public surface).

### Decisive source
```go
listTypes, err := a.core.GetListTypes(nil, req.FormListUUIDs)
for _, t := range listTypes {
	if t == models.ListTypePrivate {
		return false, echo.NewHTTPError(http.StatusBadRequest, a.i18n.T("globals.messages.invalidUUID"))
	}
}
_, hasOptin, err := a.core.InsertSubscriber(models.Subscriber{...}, nil, listUUIDs, false, true)
if e, ok := err.(*echo.HTTPError); ok && e.Code == http.StatusConflict {
	sub, err := a.core.GetSubscriber(0, "", req.Email)
	_, hasOptin, err := a.core.UpdateSubscriberWithLists(sub.ID, sub, nil, listUUIDs,
		false /*preconfirm*/, false /*deleteLists*/, true /*assertOptin*/, nil /*permitted*/, true /*allowResubscribe*/)
```

**Flow:** bind → require ≥1 list → email sanitized (importer.SanitizeEmail: lowercase/trim/mail.ParseAddress bare-address + domain allow/blocklist) → name defaults to local-part of email → PRIVATE LIST PROBE: any requested list resolving to type=private rejects the WHOLE request with generic invalidUUID (no enumeration) → insert (assertOptin=true so optin-mail failure surfaces) → on 409 conflict refetch by email and MERGE subscriptions with allowResubscribe=true, permitted=nil (public users may only touch lists they could see anyway — the private gate already ran). Unsub side: SubscriptionPrefs unsubscribes by campaign UUID or flips blocklist flag gated on Privacy.AllowBlocklist; preference management filters out private lists before diffing checked vs stored.
**Invariant:** Private-list membership is checked BEFORE any DB write and again at page-render time (`SubscriptionPage` skips type=private rows) — the same list can never be joined or even listed via the public surface. assertOptin=true makes double-optin mail delivery part of the request contract.
**Probe:** `bash -c "cd <repo> && grep -c ListTypePrivate cmd/public.go"` → 3; `grep -cF 'allowResubscribe' internal/core/subscribers.go` → 2.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "processSubForm public subscribe", limit: 10 });
```
## Verdict
Adopt gate-before-write public subscription with merge-on-conflict resubscribe. Adapt captcha hooks (Altcha provider lives beside this plane) freely. Omit i18n templates.
