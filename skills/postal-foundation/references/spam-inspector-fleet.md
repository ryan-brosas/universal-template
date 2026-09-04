<!-- capsule-v2 -->
# Spam/virus inspector fleet — how do you fan a message out to rspamd/spamassassin + ClamAV without letting a scanner outage block delivery?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `postal`. **Question:** Which scanners run for which scope, what wire protocols do they speak, and what happens on each scanner's timeout/error?

## MessageInspector selection + three inspectors
**Path/Symbol:** `lib/postal/message_inspector.rb:MessageInspector.inspectors` (26–40); `lib/postal/message_inspectors/spam_assassin.rb:SpamAssassin#inspect_message` (12–53); `lib/postal/message_inspectors/rspamd.rb:Rspamd` (7–74); `lib/postal/message_inspectors/clamav.rb:Clamav#inspect_message` (7–47).
**Signature:** `MessageInspector.inspectors → [inspector…]`; concrete inspectors implement `inspect_message(inspection)` mutating the shared `Postal::MessageInspection` (`spam_checks <<`, `threat=`, `threat_message=`).
**Data Shape:** `EXCLUSIONS = { outgoing: ["NO_RECEIVED", "NO_RELAYS", "ALL_TRUSTED", "FREEMAIL_FORGED_REPLYTO", "RDNS_DYNAMIC", "CK_HELO_GENERIC", /^SPF_/, /^HELO_/, /DKIM_/, /^RCVD_IN_/], incoming: [] }` — outgoing mail drops relay/SPF/DKIM-internal rules that are meaningless off-network.

### Decisive source
```ruby
# selection: rspamd XOR spamassassin, plus ClamAV independently
if Postal::Config.rspamd.enabled?      then inspectors << MessageInspectors::Rspamd.new(...)
elsif Postal::Config.spamd.enabled?    then inspectors << MessageInspectors::SpamAssassin.new(...) end
if Postal::Config.clamav.enabled?      then inspectors << MessageInspectors::Clamav.new(...) end

# SpamAssassin: raw spamd socket protocol, 15 s budget
Timeout.timeout(15) do
  tcp_socket = TCPSocket.new(@config.host, @config.port)
  tcp_socket.write("REPORT SPAMC/1.2\r\n")
  tcp_socket.write("Content-length: #{raw_message.bytesize}\r\n\r\n")
  tcp_socket.write(raw_message); tcp_socket.close_write
  data = tcp_socket.read
end
# parse "score code description" lines; continuation lines append to previous description
checks = spam_checks.reject { |s| EXCLUSIONS[inspection.scope].include?(s.code) }

# Rspamd outbound trick — empty IP still flips rspamd to its outbound profile:
if scope == :outgoing
  request["User"] = ""
  request["Ip"] = ""     # https://rspamd.com/doc/tutorials/scanning_outbound.html
end

# ClamAV: length-prefixed chunked stream
tcp_socket.write("zINSTREAM\0")
tcp_socket.write([raw_message.bytesize].pack("N"))
tcp_socket.write(raw_message)
tcp_socket.write([0].pack("N"))
```

**Flow:** `MessageInspection.scan` iterates every enabled inspector → each appends `SpamCheck(code, score, description)` rows or sets threat fields → failures NEVER raise: spam scanners append score-0 `TIMEOUT`/`ERROR` check rows (visible in the UI, score-neutral); ClamAV sets `threat=false` with "Timed out/Error when scanning" (fail-open).
**Invariant:** The two failure postures are deliberately asymmetric and must stay distinguishable when porting: a dead spam scanner yields an *auditable* zero-score row, while a dead virus scanner silently passes the message. Rspamd wins over spamd when both are configured (elsif). Outgoing scope suppresses network-topology rules via EXCLUSIONS *and* the empty-IP header.
**Probe:** No dedicated spec drives any inspector class at this pin (search_graph/spec-tree check: only processor specs exist, and they stub `Postal::MessageInspection.scan`). Coverage caveat recorded here: protocol behavior is pinned by direct source read only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "postal", query: "spam check inspect message rspamd clamav spamd timeout", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the inspector-registry pattern (config-driven selection, shared mutable inspection object), per-scanner timeouts, scope-based rule exclusions, and the auditable-vs-fail-open error split. Adapt wire protocols to your scanner fleet. Omit the spamd raw-socket parser if you only run rspamd.
