<!-- capsule-v2 -->
# Finished terminal gates — which checks run between end-of-body and "250 OK", and how does failure reset without killing the connection?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `postal`. **Question:** How do you validate a fully received message (size, loops, sender identity) and persist per-recipient copies while keeping the session reusable after a rejection?

## Client#finished
**Path/Symbol:** `app/lib/smtp_server/client.rb:SMTPServer::Client#finished` (:464–544, read directly — graph snippet had a recovery artifact in the `:bounce` branch; source is ground truth).
**Signature:** `finished → "250 OK"|"552 …"|"550 Loop detected"|"530 From/Sender name is not valid"`.
**Data Shape:** gates read `@data.bytesize`, folded `@headers["received"]`, and `@credential`; persistence fans out over `@recipients` tuples into per-server MessageDB rows (`scope`, `bounce`, `credential_id`, `domain_id` fields).

### Decisive source
```ruby
if @data.bytesize > Postal::Config.smtp_server.max_message_size.megabytes.to_i
  transaction_reset; @state = :welcomed
  increment_error_count("message-too-large")
  return format("552 Message too large (maximum size %dMB)", ...)
end

if @headers["received"].grep(/by #{Postal::Config.postal.smtp_hostname}/).count > 4
  transaction_reset; @state = :welcomed
  increment_error_count("loop-detected")
  return "550 Loop detected"
end

if @credential
  authenticated_domain = @credential.server.find_authenticated_domain_from_headers(@headers)
  if authenticated_domain.nil?
    ... return "530 From/Sender name is not valid"
  end
end

@recipients.each do |type, rcpt_to, server, options|
  case type
  when :credential then ... message.scope = "outgoing"; message.credential_id = @credential.id ...
  when :bounce     then rp_route ? route.create_messages { |m| m.bounce = 1 }   # via __returnpath__ route
                                 : (message.scope = "incoming"; message.bounce = 1; message.save)
  when :route      then options[:route].create_messages { |msg| ... }
  end
end
transaction_reset; @state = :welcomed; "250 OK"
```

**Flow:** size gate (byte-accurate, MB config) → loop gate (>4 Received hops naming this host) → credential gate (From/Sender headers must resolve to a domain the credential's server actually owns) → fan-out persistence per recipient type → envelope cleared, state back to `:welcomed` so the same connection can send again.
**Invariant:** every rejection path performs the same `transaction_reset` + `@state = :welcomed` as success — rejection never strands the session in body mode nor destroys the connection; the loop detector counts only *its own* hostname inside Received headers, so third-party relay chains don't false-positive; bounce storage has two forms (route-mediated when a `__returnpath__` route exists, direct insert otherwise) but both stamp `bounce = 1`.
**Probe:** `spec/lib/smtp_server/client/finished_spec.rb:44–82` (10MB body vs 1MB limit ⇒ 552; four self-hostname Received lines ⇒ 550; wrong From domain ⇒ 530 — all "resets the state"); :84–103 (outgoing ⇒ QueuedMessage with server/domain attributes); :117–200 (bounce via return-path route / direct insert / incoming route).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "postal", qualified_name: "postal.app.lib.smtp_server.client.SMTPServer.Client.finished" });
```

## Verdict
Adopt the gate order (cheap byte check → loop heuristic → identity check → persistence) and the uniform reject-and-reset epilogue that keeps sessions hot. Adapt the loop-detection signal to whatever hop evidence your protocol preserves. Omit MessageDB specifics (covered by `message-db-per-server` capsule).
