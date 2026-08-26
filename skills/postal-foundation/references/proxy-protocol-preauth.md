<!-- capsule-v2 -->
# PROXY protocol preauth — how do you accept a real client IP from a load balancer without ever trusting it twice?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `postal`. **Question:** How should a TCP server behind HAProxy's proxy protocol learn the client IP before any application bytes, and what happens on a malformed header?

## Client#proxy + server accept path
**Path/Symbol:** `app/lib/smtp_server/client.rb:SMTPServer::Client#proxy` (:118–132), `check_ip_address` (:36–42); `app/lib/smtp_server/server.rb:run_event_loop` (accept branch).
**Signature:** `proxy(data) → "220 <hostname> ESMTP Postal/<trace_id>" | "502 Proxy Error"`.
**Data Shape:** header grammar `PROXY <inet-protocol> <client-ip> <proxy-ip> <client-port> <proxy-port>`; client constructed as `Client.new(nil)` — identity unknown until the header lands.

### Decisive source
```ruby
def proxy(data)
  if m = data.match(/\APROXY (.+) (.+) (.+) (.+) (.+)\z/)
    @ip_address = m[2]              # field 2 is the CLIENT ip, not the proxy's
    check_ip_address
    @state = :welcome               # only now does the session enter the command phases
    increment_command_count("PROXY")
    return "220 #{Postal::Config.postal.smtp_hostname} ESMTP Postal/#{trace_id}"
  end
  @finished = true                  # malformed ⇒ connection terminates, not just an error reply
  increment_error_count("proxy-error")
  "502 Proxy Error"
end
```
```ruby
# server accept branch — welcome is DEFERRED under proxy protocol
if Postal::Config.smtp_server.proxy_protocol?
  client = Client.new(nil)          # no banner yet: we don't know who we're talking to
else
  client = Client.new(client_ip_address)   # ::ffff: stripped from remote_address first
  new_io.print("220 #{...} ESMTP Postal/#{client.trace_id}")
end
```

**Flow:** with `proxy_protocol` enabled, accepted sockets get `Client.new(nil)` and `@state = :preauth`; `handle` routes every line in that state straight to `proxy(data)`; a well-formed header sets `@ip_address`, runs the blocklist check, advances to `:welcome`, and emits the banner; anything else marks `@finished` so the event loop closes the socket.
**Invariant:** exactly ONE preauth line is honored and the banner is never sent before identity is known — an attacker cannot interleave SMTP commands before the header, and cannot spoof after it (`check_ip_address` still applies); malformed headers fail closed (disconnect + labeled counter), unlike ordinary command errors which keep the session.
**Probe:** `spec/lib/smtp_server/client/proxy_spec.rb` (:1–29, seven expectations around valid/invalid PROXY lines and post-header state).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "postal", qualified_name: "postal.app.lib.smtp_server.client.SMTPServer.Client.proxy" });
```

## Verdict
Adopt deferred-banner preauth with a one-shot strict parser whose failure disconnects. Adapt the regex to PROXY v2 binary headers if you need them. Omit postal's trace-id banner format.
