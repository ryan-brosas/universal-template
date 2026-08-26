<!-- capsule-v2 -->
# tx-message-subscriber-modes — How does the transactional send API resolve recipients that may not exist?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** What do subscriber_mode default|fallback|external actually change, and which combinations are rejected?

## Three-mode recipient resolution
**Path/Symbol:** `cmd/tx.go:SendTxMessage` (:17-178, resolution loop :80-135), `validateTxMessage` (:181-247); mode consts `models/messages.go:45-47`; cached template source `manager.GetTpl/CacheTpl` (`internal/manager/manager.go:313-336`).
**Signature:** modes `default | fallback | external` on TxMessage{SubscriberEmails []string, SubscriberIDs []int, ...}.
**Data Shape:** singleton compat fields subscriber_email/subscriber_id fold into slices; multipart form variant carries JSON in `data` field + files as attachments.

### Decisive source
```go
if m.SubscriberMode == models.TxSubModeExternal {
	// Always create an ephemeral "subscriber" and don't lookup in the DB.
	sub = models.Subscriber{Email: m.SubscriberEmails[n]}
} else {
	sub, err = a.core.GetSubscriber(subID, "", subEmail)
	if er.Code == http.StatusBadRequest {
		if m.SubscriberMode == models.TxSubModeFallback {
			sub = models.Subscriber{Email: subEmail} // ephemeral on miss
		} else {
			notFound = append(notFound, ...); continue // default: skip+report
		}
	}
}
...
if len(notFound) > 0 { return echo.NewHTTPError(http.StatusBadRequest, strings.Join(notFound, "; ")) }
```

**Flow:** validate (emails XOR ids for default; fallback/external REJECT ids entirely) → sanitize every email through the importer choke point → per recipient: external never touches DB; default skips-and-collects misses (200 only if none missed); fallback fabricates ephemeral subscriber so arbitrary addresses receive mail → render each message against the CACHED compiled template (CacheTpl precompiles + inline-embeds at template save time) → PushMessage with 3s bounded timeout; any push timeout aborts the whole request with error.
**Invariant:** default-mode partial success is REPORTED not silent — the response is 400 listing every miss even though the found ones were already pushed (at-least-once with explicit accounting). Template caching moves compile cost off the hot path but means template edits must invalidate the cache explicitly.
**Probe:** `bash -c "cd <repo> && grep -rn 'TxSubMode' models/messages.go"` → 3 consts (:45-47); `grep -cF 'notFound = append(notFound,' cmd/tx.go` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "SendTxMessage subscriber_mode", limit: 10 });
```
## Verdict
Adopt tri-mode resolution for any "send to known or unknown humans" API. Adapt to your user store. Omit multipart binding specifics.
