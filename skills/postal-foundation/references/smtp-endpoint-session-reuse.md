<!-- capsule-v2 -->
# SMTP endpoint session reuse — how do you deliver a whole batch over warm SMTP connections without mixing up messages?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `ext-postal`. **Question:** How does the sender resolve servers, pick endpoints, downgrade SSL safely, and recover from mid-session connection resets?

## SMTPSender + SMTPClient::Endpoint
**Path/Symbol:** `app/senders/smtp_sender.rb:start` (27–37), send_message (40–69), connect_to_endpoint (179–208), send_message_to_smtp_client (87–137), determine_mail_from_for_message (139–153), .smtp_relays (241–255); `app/lib/smtp_client/endpoint.rb:start_smtp_session` (54–97), send_message (100–117); `app/lib/smtp_client/server.rb:endpoints` (20–31).
**Signature:** `SMTPSender.new(domain, source_ip_address = nil, servers: nil, log_id: nil, rcpt_to: nil)`; `start → Endpoint|false`; `send_message(message) → SendResult`; `Endpoint#send_message(raw, mail_from, [rcpt], retry_on_connection_error: true)`.
**Data Shape:** Server = `{hostname, port=25, ssl_mode ∈ Auto|STARTLS|TLS|None}`; Endpoint = server × resolved IP; sender keeps `@current_endpoint`, `@endpoints` (tried list), `@connection_errors` (dedup).

### Decisive source
```ruby
# start — resolution precedence: forced servers > configured relays > MX > domain A fallback
servers = @servers || self.class.smtp_relays || resolve_mx_records_for_domain || []
servers.each do |server|
  server.endpoints.each do |endpoint|          # AAAA first, then A
    result = connect_to_endpoint(endpoint)
    return endpoint if result                   # first live session wins
  end
end
false

def connect_to_endpoint(endpoint, allow_ssl: true)
  if @source_ip_address && @source_ip_address.ipv6.blank? && endpoint.ipv6?
    return false                                 # source IP family must support the target
  end
  @endpoints << endpoint unless @endpoints.include?(endpoint)
  endpoint.start_smtp_session(allow_ssl: allow_ssl, source_ip_address: @source_ip_address)
  @current_endpoint = endpoint; true
rescue StandardError => e
  endpoint.finish_smtp_session                   # never leak half-open sockets
  if e.is_a?(OpenSSL::SSL::SSLError) && endpoint.server.ssl_mode == "Auto"
    return connect_to_endpoint(endpoint, allow_ssl: false)   # Auto downgrades ONCE per level
  end
  @connection_errors << e.message unless @connection_errors.include?(e.message)
  false
end

# endpoint.rb — one silent retry after rebuilding the session
def send_message(raw_message, mail_from, rcpt_to, retry_on_connection_error: true)
  raise SMTPSessionNotStartedError if @smtp_client.nil? || !@smtp_client.started?
  @smtp_client.rset_errors
  @smtp_client.send_message(raw_message, mail_from, [rcpt_to])
rescue Errno::ECONNRESET, Errno::EPIPE, OpenSSL::SSL::SSLError
  if retry_on_connection_error
    finish_smtp_session; start_smtp_session
    return send_message(raw_message, mail_from, rcpt_to, retry_on_connection_error: false)
  end
  raise
end
```

**Flow:** `start` walks every MX host's endpoints until one session sticks (IPv6 tried first within each host) → each message goes over the CURRENT warm session; State caches the whole sender per `(SMTPSender, [domain, ip])` so batch siblings reuse it (`sender_for`) and only a cached `connect_error` result short-circuits further attempts → `finish` closes every tried endpoint's session at batch end. MAIL FROM is VERP-style: bounce ⇒ empty string, valid custom return-path ⇒ `server.token@return_path_domain`, else global return-path.
**Invariant:** SSL verify mode is tied to ssl_mode: explicit STARTTLS/TLS get `VERIFY_PEER` with system cert store; `Auto` probes with VERIFY_NONE first and downgrades to plaintext on SSLError — but a hard-configured TLS mode NEVER downgrades. Connection-reset recovery is exactly ONE rebuild+retry (`retry_on_connection_error:` flag prevents recursion); the reset ladder (`reset_smtp_session` → RSET, falling back to full finish) is called by the RESULT handlers in smtp_sender before SoftFail classification. `send_message` with no live endpoint returns SoftFail + `connect_error: true` (which caches into State and stops sibling sends early).
**Probe:** `spec/senders/smtp_sender_spec.rb:47–212` (relay override, no-MX fallback, IPv6-family skip, SSL Auto downgrade, second-server failover), :365–384 (retry parsed from "30 seconds"⇒40 / "5 minutes"⇒310 — executed this pass as deterministic probe), :505–525 (finish closes all endpoints); `spec/lib/smtp_client/endpoint_spec.rb`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-postal", query: "connect_to_endpoint start_smtp_session smtp_relays resolve_mx_records", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the resolution precedence chain, endpoint walking with family gating, Auto-SSL probe-then-downgrade (explicit modes never downgrade), single-shot session-rebuild retry, per-(domain,ip) sender caching for batches, and dedup'd connection-error collection for honest failure details. Adapt Net::SMTP to your SMTP library, keeping the timeout trio (`open_timeout/read_timeout/tls_hostname`). Omit VERP token formats.
