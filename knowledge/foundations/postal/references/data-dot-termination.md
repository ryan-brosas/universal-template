<!-- capsule-v2 -->
# DATA dot-termination — how do you stream an SMTP body line-by-line while keeping headers, dot-stuffing, and CR discipline exact?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `postal`. **Question:** How does the server swap its per-line handler for body mode, un-dot-stuff, accumulate headers for later loop detection, and terminate on `.` without off-by-one CR bugs?

## Client#data
**Path/Symbol:** `app/lib/smtp_server/client.rb:SMTPServer::Client#data` (:409–462).
**Signature:** `data(_data) → "354 Go ahead"`; installs `@proc` handler receiving each subsequent line; terminator path returns the `finished` verdict string.
**Data Shape:** `@data` binary-forced buffer (Received header prepended); `@headers` = lowercase-name → array-of-values with continuation-line folding; `@receiving_headers` flips on first empty line.

### Decisive source
```ruby
handler = proc do |idata|
  if idata == "." && @cr_present && @previous_cr_present   # BOTH lines must be CRLF-legal
    @logging_enabled = true; @proc = nil; finished          # hand verdict back to caller
  else
    idata = idata.to_s.sub(/\A\.\./, ".")                   # RFC 5321 dot-stuffing reversed once
    if @receiving_headers
      if idata&.length&.zero?        then @receiving_headers = false
      elsif idata.to_s =~ /^\s/      then @headers[@header_key.downcase].last << idata  # folded continuation
      else @header_key, value = idata.split(/:\s*/, 2)
           @headers[@header_key.downcase] ||= []; @headers[@header_key.downcase] << value
      end
    end
    @data << idata << "\r\n"
    nil                                          # nil ⇒ event loop writes nothing yet
  end
end
@proc = handler
"354 Go ahead"
```

**Flow:** phase gate requires `:rcpt_to_received` → generate own `Received:` header into buffer+index → swap dispatcher for the proc → per line: un-stuff leading `..`, fold/collect headers until blank line, append raw bytes → a legal bare `.\<CR>` ends body mode and synchronously runs the terminal gates (`finished`) whose reply string is written by the event loop.
**Invariant:** the terminator only counts when the current line AND the previous line ended with `<CR>` (`@cr_present && @previous_cr_present`, maintained in `handle`'s `ensure`) — this is what makes `.\r` vs bare `.` tests deterministic; header names are downcased and folded continuations append to the last value so `grep` over `@headers["received"]` is reliable for loop detection; the injected Received header means every stored message carries server-verified hop data.
**Probe:** `spec/lib/smtp_server/client/data_spec.rb:27–85` (354 after full envelope; Received header text pinned via Timecop; multi-value + folded header capture: `"x-multiline" => ["1234             4567"]`; exact `@data` byte-equality incl. `\r\n`); `spec/lib/smtp_server/client/finished_spec.rb:25–42` (bare `.` and `.\r`-after-bare-line both do nothing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "postal", qualified_name: "postal.app.lib.smtp_server.client.SMTPServer.Client.data" });
```

## Verdict
Adopt handler-swap body mode, single-pass dot-unstuffing, two-line CR gating of the terminator, and header folding into a name→values index. Adapt the proc idiom to your language's closure/continuation norms. Omit postal's log-suppression branch (`log_smtp_data?`) if you have no equivalent privacy toggle.
