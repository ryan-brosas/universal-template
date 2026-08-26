<!-- capsule-v2 -->
# email-domain-allow-blocklist — Where does domain gating live and how do wildcard rules match?

**Source:** listmonk AGPL-3.0 `master@670c0171`; Codebase Memory `ext-listmonk`. **Question:** What is the single choke point every inbound email passes through, and what are the wildcard semantics?

## SanitizeEmail choke point + first-label wildcard
**Path/Symbol:** `internal/utils/utils.go:SanitizeEmail` (:25-32, bare-address canonicalizer); `internal/subimporter/importer.go:SanitizeEmail` (:611-640 domain gate), `checkInList` (:671-695), `makeDomainMap` (:747-762); callers: processSubForm (public), validateBounceFields (webhooks), ValidateFields (import), validateTxMessage (tx).
**Signature:** `func (im *Importer) SanitizeEmail(email string) (string, error)`; `checkInList(domain string, hasWildcards bool, mp map[string]struct{}) bool`.
**Data Shape:** config lists DomainBlocklist/DomainAllowlist; maps precompiled at New() with hasWildcards flags.

### Decisive source
```go
if im.hasAllowlist {
	if !im.checkInList(domain, im.hasAllowlistWildcards, im.domainAllowlist) {
		return "", errors.New(im.i18n.T("subscribers.domainBlocklisted"))
	}
} else if im.hasBlocklist {
	if im.checkInList(domain, im.hasBlocklistWildcards, im.domainBlocklist) {
		return "", errors.New(...)
	}
}
...
// makeDomainMap: *.example.com ALSO registers bare example.com
if strings.Contains(d, "*.") { hasWildCards = true; out[strings.TrimPrefix(d, "*.")] = struct{}{} }
// checkInList subdomain fallback: test.mail.example.com => *.mail.example.com
parts[0] = "*"
```

**Flow:** lowercase/trim → mail.ParseAddress must succeed AND round-trip exactly (display names rejected) → if allowlist configured, domain MUST match (blocklist then moot); else blocklist match rejects → wildcard path only when list contains any `*.` entry AND domain has >1 dot: replace FIRST label with `*` and re-probe. Error message deliberately REUSES the "domain blocklisted" i18n key for allowlist misses (no mode disclosure).
**Invariant:** One canonicalization point means bounce-matching, imports, tx sends, and public signups compare IDENTICAL lowercase strings — porters who add a second validation site create drift where an address subscribes but its bounces can't match it. Allowlist-wins-over-blocklist precedence is explicit.
**Probe:** `bash -c "cd <repo> && grep -cF 'strings.TrimPrefix(d, \"*.\")' internal/subimporter/importer.go"` → 1; `grep -c 'func.*SanitizeEmail' internal/utils/utils.go internal/subimporter/importer.go` → 2 lines (wrapper + core).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-listmonk", query: "SanitizeEmail domain allowlist", limit: 10 });
```
## Verdict
Adopt single-chokpoint canonicalization with precompiled lists and first-label wildcards. Adapt to your identity system's normalization. Omit i18n keys.
