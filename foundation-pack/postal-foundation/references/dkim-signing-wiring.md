<!-- capsule-v2 -->
# DKIM signing wiring — where in the send pipeline does signing attach, and what key/signer object does it use?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `postal`. **Question:** At which dequeuer gate is the DKIM header appended, and how are the RSA key and webhook-signing roles separated?

## Signer + add_outgoing_headers chain
**Path/Symbol:** `lib/postal/signer.rb:Postal::Signer` (5–66); `app/lib/message_dequeuer/outgoing_message_processor.rb:add_outgoing_headers` (112–116); `lib/postal/message_db/message.rb:add_outgoing_headers` (413–421).
**Signature:** `Signer.new(OpenSSL::PKey::RSA)` → `#sign(data)` (raw SHA256), `#sign64(data)` (strict base64), `#sha1_sign64` (legacy), `#jwk` (`JWT::JWK`, `use:"sig", alg:"RS256"`), `attr_reader :private_key`.
**Data Shape:** `Postal.signer` is the process-wide Signer built from the global private key — it serves BOTH DKIM fallback signing and webhook request signatures. `Message#add_outgoing_headers` appends headers into the message DB's raw header row via `append_headers`.

### Decisive source
```ruby
# outgoing_message_processor.rb:112–116 — gate position inside process:
#   … hold_if_recipient_on_suppression_list → parse_content → inspect_message
#   → fail_if_spam → add_outgoing_headers → check_send_limits …
def add_outgoing_headers
  return if queued_message.message.has_outgoing_headers?   # idempotence: MsgID already present
  queued_message.message.add_outgoing_headers
end

# lib/postal/message_db/message.rb:406–421
def has_outgoing_headers?
  !!(raw_headers =~ /^X-Postal-MsgID:/i)   # the MsgID header IS the "already signed" latch
end

def add_outgoing_headers
  headers = []
  if domain
    dkim = DKIMHeader.new(domain, raw_message)
    headers << dkim.dkim_header            # signed LAST, after tracking + spam headers
  end
  headers << "X-Postal-MsgID: #{token}"    # always appended, DKIM or not
  append_headers(*headers)
end
```

**Flow:** dequeuer ladder reaches `add_outgoing_headers` AFTER parse/inspect/spam-fail gates → skip if an `X-Postal-MsgID:` header already exists (retry-safe idempotence, case-insensitive match on raw headers) → DKIMHeader builds+signs against the current raw bytes → X-Postal-MsgID always stamped.
**Invariant:** Signing is a late gate: anything that mutates raw content after this point invalidates the signature, so content rewrites must stay ordered before it. A message with no `domain` association still gets its MsgID but NO signature — absence of domain must not raise. The Signer object deliberately multiplexes two trust roles (DKIM identity fallback + webhook signing); splitting them changes key-rotation blast radius.
**Probe:** `spec/lib/message_dequeuer/outgoing_message_processor_spec.rb:240–261` (without a from-domain no `dkim-signature` header is stored but `x-postal-msgid` still appears; with one, headers contain `\Av=1; a=rsa-sha256`). `spec/lib/postal/signer_spec.rb` (full, 79 lines) verifies sign/sign64/sha1_sign64 by public-key round-trip and JWK type.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "postal", query: "Signer sign64 webhook signature private key", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the late-gate signing position, the MsgID-header idempotence latch, and the MsgID-always/DKIM-conditional split. Adapt the idempotence marker (any stable "already processed" header works) to your queue's retry model. Omit SHA1 helpers unless you need Postal-compatible legacy webhook signatures. Coverage note: all cited paths reported `no_recorded_issue` on check_index_coverage at this pin.
