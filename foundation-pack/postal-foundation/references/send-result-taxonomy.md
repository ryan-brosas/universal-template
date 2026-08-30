<!-- capsule-v2 -->
# SendResult taxonomy — what does a sender return, and how do SMTP/HTTP failures map onto it?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `ext-postal`. **Question:** How are delivery outcomes classified so the dequeuer can decide destroy vs retry vs bounce without knowing transport details?

## SendResult + exception mapping
**Path/Symbol:** `app/senders/send_result.rb:SendResult` (1–20); `app/senders/smtp_sender.rb:send_message_to_smtp_client` (87–137), create_result (220–239); `app/senders/http_sender.rb:send_message` (14–55).
**Signature:** `create_result(type, start_time = nil) { |r| … } → SendResult`; fields `type, details, output, secure, connect_error, retry, suppress_bounce, log_id, time`.
**Data Shape:** `type ∈ {"Sent","SoftFail","HardFail","Held","Processed","Error"}` (dequeuer consumes Sent/SoftFail/HardFail from senders); `retry` is `true | Integer(seconds) | nil`; `connect_error: true` marks "no session was possible" (State caches it).

### Decisive source
```ruby
rescue Net::SMTPServerBusy, Net::SMTPAuthenticationError, Net::SMTPSyntaxError,
       Net::SMTPUnknownError, Net::ReadTimeout => e
  @current_endpoint.reset_smtp_session
  create_result("SoftFail", start_time) do |r|
    r.details = "Temporary SMTP delivery error when sending to #{@current_endpoint}"
    r.output = e.message
    if e.message =~ /(\d+) seconds/            # parse server-supplied retry hints
      r.retry = ::Regexp.last_match(1).to_i + 10
    elsif e.message =~ /(\d+) minutes/
      r.retry = (::Regexp.last_match(1).to_i * 60) + 10
    else
      r.retry = true                           # default backoff (1.3^n)
    end
  end
rescue Net::SMTPFatalError => e                # 5xx permanent
  create_result("HardFail", start_time) { |r| r.output = e.message }
rescue StandardError => e                      # unknown ⇒ treat as transient
  create_result("SoftFail", start_time) { |r| r.retry = true }

# HTTPSender — status-code keyed classification
if response[:code] >= 200 && response[:code] < 300   then result.type = "Sent"
elsif response[:code] >= 500 && response[:code] < 600 then result.type = "SoftFail"; result.retry = true
elsif response[:code].negative?                       # AddressGuard negative codes
  result.type = "SoftFail"; result.retry = true; result.connect_error = true
elsif response[:code] == 429                          # rate limit: give up QUIETLY
  result.type = "HardFail"; result.suppress_bounce = true
else result.type = "HardFail"
end
```

**Flow:** every send path funnels into one SendResult; the dequeuer's `finish_processing` reads only `.retry` (requeue with parsed delay or default backoff) and `.type`; `log_sender_result` turns details/output/secure/log_id/time into the immutable delivery record; incoming additionally bounces on HardFail unless `suppress_bounce`.
**Invariant:** temporary-vs-permanent is decided by the SENDER, never the dequeuer. Unknown exceptions default to SoftFail (availability over accuracy) but SMTPFatalError (remote said "no, ever") is HardFail. The `+10 s` slack on parsed retry hints prevents immediate re-delivery at the boundary. 429 gets HardFail WITH bounce suppression so a rate-limited webhook endpoint can't trigger bounce storms. `secure` is captured from the live socket (`smtp_client.secure_socket?`) per attempt.
**Probe:** `spec/senders/smtp_sender_spec.rb:334–502` (busy/auth/syntax/unknown⇒SoftFail+session reset; fatal⇒HardFail; retry 30s→40, 5min→310); deterministic probes executed this pass for the regex ladder and HTTP classification table.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-postal", query: "SendResult create_result suppress_bounce connect_error", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the result-object contract with parsed server retry hints, the fail-open-for-unknown/fail-closed-for-5xx SMTP mapping, and status-keyed HTTP classification including 429 bounce suppression and negative-code connect errors. Adapt type strings and backoff constants to your domain vocabulary.
