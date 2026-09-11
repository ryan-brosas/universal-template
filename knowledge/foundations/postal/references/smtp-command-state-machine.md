<!-- capsule-v2 -->
# SMTP command state machine — how do you gate a line protocol so each verb is only legal in the right phase?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `postal`. **Question:** How does an SMTP server enforce per-phase command legality, reset transaction state cleanly, and survive hostile line endings without a parser library?

## Client#handle → handle_command → in_state
**Path/Symbol:** `app/lib/smtp_server/client.rb:SMTPServer::Client` (`handle` :55–78, `handle_command` :90–108, `in_state` :546–548, `transaction_reset` :44–49, `mail_from` :286–303).
**Signature:** `handle(data) → response_string|nil`; `handle_command(data) → "code text"`; `in_state(*states) → Boolean`.
**Data Shape:** client holds `@state ∈ {:preauth, :welcome/:welcomed, :mail_from_received, :rcpt_to_received}`; every handler returns an SMTP reply string or nil; multi-line modes swap `@proc` to a continuation proc that `handle` calls instead of `handle_command`.

### Decisive source
```ruby
# handle_command — dispatch IS the grammar; unknown verbs are just another error label
when /^MAIL FROM/i      then mail_from(data)
...
else
  increment_error_count("invalid-command")
  "502 Invalid/unsupported command"

# mail_from — phase gate first, then state advance, then scrub untrusted input
unless in_state(:welcomed, :mail_from_received)
  increment_error_count("mail-from-out-of-order")
  return "503 EHLO/HELO first please"
end
@state = :mail_from_received
transaction_reset                      # fresh MAIL FROM discards prior envelope
if data =~ /AUTH=/
  # Discard AUTH= parameter ... we don't trust any client to set it
  mail_from_line = data.sub(/ *AUTH=.*/, "")
end

# handle — bare-CR discipline is tracked across lines, not raised
if data[-1] == "\r" then @cr_present = true; data = data.chop
else Postal.logger&.warn("Detected line with invalid line ending (missing <CR>)", trace_id: trace_id); @cr_present = false end
...
ensure
  @previous_cr_present = @cr_present
```

**Flow:** accept → `:welcome` (or `:preauth` under proxy protocol) → EHLO/HELO keeps state → `MAIL FROM` requires welcome-phase, advances to `:mail_from_received`, resets envelope → `RCPT TO` requires mail-from phase → `DATA` requires rcpt phase and swaps in a body proc → terminal gates reset to `:welcomed`. Every illegal transition returns 503 with a Prometheus-labeled error count instead of raising.
**Invariant:** state transitions and error replies are total — no path raises on bad input; `AUTH=` is always stripped from MAIL FROM (never trusted); transaction state (`@recipients/@mail_from/@data/@headers`) only ever cleared via `transaction_reset`; CR presence is remembered one line back because dot-termination legality spans two lines.
**Probe:** `spec/lib/smtp_server/client/data_spec.rb:12–25` (DATA before HELO/MAIL/RCPT ⇒ 503 each step); `spec/lib/smtp_server/client/mail_from_spec.rb`; `spec/lib/smtp_server/client/helo_spec.rb`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "postal", qn_pattern: ".*smtp_server.*", fields: ["lines"], limit: 40 });
```

## Verdict
Adopt the phase-gate pattern (check `in_state` → labeled error counter → reply string) and the two-line CR memory as the cheap way to make line protocols robust. Adapt state names/reply codes to your protocol; replace Rails/Prometheus plumbing. Omit postal's specific bounce/route semantics (see sibling capsule).
