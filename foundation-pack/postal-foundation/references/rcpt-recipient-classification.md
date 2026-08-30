<!-- capsule-v2 -->
# RCPT TO recipient classification — how do you turn one envelope verb into four different routing outcomes plus IP-trust fallback?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `postal`. **Question:** How does a single `RCPT TO` handler decide between bounce collection, token-routed incoming, authenticated outgoing, route-matched incoming, and unauthenticated relay — and how is IP-based trust resolved safely?

## Client#rcpt_to
**Path/Symbol:** `app/lib/smtp_server/client.rb:SMTPServer::Client#rcpt_to` (:305–407).
**Signature:** `rcpt_to(data) → "250 OK"|"4xx/5xx string"`; appends `[type, rcpt_to, server, options?]` to `@recipients`.
**Data Shape:** address parsed to `uname, domain` (plus `+tag` sub-addressing); recipient tuple type ∈ `{:bounce, :route, :credential}`; `@credential` set by AUTH or discovered from `Credential.where(type: "SMTP-IP")`.

### Decisive source
```ruby
elsif domain == Postal::Config.dns.return_path_domain ||
      domain =~ /\A#{Regexp.escape(Postal::Config.dns.custom_return_path_prefix)}\./
  # bounce collection: local part is a SERVER TOKEN, not a mailbox
  if server = ::Server.where(token: uname).first
    ... @recipients << [:bounce, rcpt_to, server]
elsif domain == Postal::Config.dns.route_domain
  # direct-to-route tokens
  @recipients << [:route, "#{route.name}#{tag ? "+#{tag}" : ''}@#{route.domain.name}", route.server, { route: route }]
elsif @credential
  # outgoing mail for an already-authenticated user
  @recipients << [:credential, rcpt_to, @credential.server]
else
  # relay attempt without auth → try longest-prefix IP credential, then retry ONCE via recursion
  @credential = Credential.where(type: "SMTP-IP").all
                          .sort_by { |c| c.ipaddr&.prefix || 0 }.reverse
                          .find { |c| c.ipaddr.include?(@ip_address) ||
                                      (c.ipaddr.ipv4? && c.ipaddr.ipv4_mapped.include?(@ip_address)) }
  if @credential then @credential.use; rcpt_to(data)   # re-run classification with credential set
  else increment_error_count("authentication-required"); "530 Authentication required" end
end
```

**Flow:** phase gate (`in_state(:mail_from_received, :rcpt_to_received)` else 503) → strip `<...>`/`RCPT TO:` decoration, split `uname+tag@domain` → classify by domain first (return-path/custom-prefix ⇒ bounce-by-server-token; route_domain ⇒ route token), then by session credential, then by route name+domain match, finally by CIDR trust. Every branch re-checks `server.suspended?` (535) and `route.mode == "Reject"` (550) before accepting.
**Invariant:** classification order matters — reserved domains win over user routes; a suspended/rejecting destination never enters `@recipients`; the SMTP-IP fallback sorts candidates by network prefix descending (most-specific CIDR wins) and retries classification exactly once (recursion depth bounded because `@credential` is now set); IPv4-mapped IPv6 addresses are matched through `.ipv4_mapped`.
**Probe:** `spec/lib/smtp_server/client/rcpt_to_spec.rb` (read in full this pass): out-of-order ⇒ `503`; bad/empty ⇒ 501; unknown return-path token ⇒ `550 Invalid server token`; suspended ⇒ 535; Reject route ⇒ 550; tag preserved as `name+tag1@domain` (:101–104); unmatched relay ⇒ `530 Authentication required`; `SMTP-IP` credential with key `1.0.0.0/8` accepts and tags `[:credential, …]` (:156–165).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "postal", qualified_name: "postal.app.lib.smtp_server.client.SMTPServer.Client.rcpt_to" });
```

## Verdict
Adopt the ordered classifier (reserved domains → session identity → directory lookup → CIDR trust) and the most-specific-prefix-wins IP credential search with one bounded retry. Adapt domain/token constants and the recipient-tuple shape to your host; replace ActiveRecord lookups. Omit postal's specific `__returnpath__` route convention.
