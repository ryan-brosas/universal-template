<!-- capsule-v2 -->
# smtp-pool-from-address-routing — How are multiple SMTP servers selected per message?

**Source:** listmonk AGPL-3.0 (patterns only) `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** How does the email messenger pick a server pool and what happens with no match?

## From-address bucketed round-robin
**Path/Symbol:** `internal/messenger/email/email.go` — pools map (:44-47), `NormalizeAddr` (:50-52), `New` (:54-110), `Push` (:117-140+).
**Signature:** `pools map[string][]*Server`; key = normalized from-address, "" = global fallback pool.
**Data Shape:** each Server carries auth protocol (cram|plain|login|none), TLS type (none|STARTTLS|TLS) + skip-verify flag, FromAddresses list; smtppool.Opt embedded.

### Decisive source
```go
// New: register every server in the global "" pool AND each of its from-address buckets.
e.pools[""] = append(e.pools[""], &s)
for _, addr := range s.FromAddresses {
	if key := NormalizeAddr(addr); key != "" {
		e.pools[key] = append(e.pools[key], &s)
	}
}
...
// Push: route by From; fall back to full pool for legacy behaviour.
pool := e.pools[""]
if len(e.pools) > 1 {
	if srvs := e.getPool(m.From); srvs != nil { pool = srvs }
}
```

**Flow:** boot: build auth/TLS per server config, wrap in smtppool, index into buckets (duplicates across buckets fine — same *Server pointer round-robins everywhere it appears) → Push: normalize message From → dedicated bucket wins if present else entire fleet → pool sends async via smtppool internals. Messenger interface satisfied by Name/Push/Flush/Close so campaigns and tx messages need no SMTP awareness.
**Invariant:** The empty-key pool is BOTH fallback AND superset — porters who make from-routing exclusive break unconfigured senders; porters who forget NormalizeAddr create case-mismatched buckets that silently never match. TLS skip-verify is per-server opt-in, never global.
**Probe:** `bash -c "cd <repo> && grep -cF 'e.pools[\"\"] = append(e.pools[\"\"], &s)' internal/messenger/email/email.go"` → 1; `grep -nF 'func NormalizeAddr' internal/messenger/email/email.go`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "Emailer pools Push", limit: 10 });
```
## Verdict
Adopt bucketed-pointer round-robin with superset fallback for multi-credential sending. Adapt to your SMTP lib. Omit smtppool concurrency tuning.
