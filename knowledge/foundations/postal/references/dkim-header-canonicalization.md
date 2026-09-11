<!-- capsule-v2 -->
# DKIM header canonicalization — how do you produce a relaxed/relaxed DKIM-Signature for arbitrary raw mail without a DKIM library?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `postal`. **Question:** Which headers get signed, in what order, and exactly how are header/body bytes canonicalized before hashing and signing?

## DKIMHeader
**Path/Symbol:** `app/lib/dkim_header.rb:DKIMHeader` (3–130).
**Signature:** `DKIMHeader.new(domain, raw_message_string)` → `#dkim_header → String` (the full header line, folded with CRLF+tab at 72-char signature chunks).
**Data Shape:** Input is the raw message split once on the first blank line (`gsub(/\r?\n/, "\r\n").split(/\r\n\r\n/, 2)`). Key material resolves two ways: domain with `dkim_status == "OK"` supplies `name` / `dkim_key` / `dkim_identifier`; otherwise Postal signs as its `return_path_domain` with `Postal.signer.private_key` and the configured `dkim_identifier`.

### Decisive source
```ruby
def normalized_headers
  [].tap do |new_headers|
    dkim_headers = headers.select do |h|
      h.match(/^(
        from|sender|reply-to|subject|date|message-id|to|cc|mime-version|content-type|content-transfer-encoding|
        resent-to|resent-cc|resent-from|resent-sender|resent-message-id|in-reply-to|references|list-id|list-help|
        list-owner|list-unsubscribe|list-unsubscribe-post|list-subscribe|list-post
      ):/ix)
    end
    dkim_headers.each { |h| new_headers << normalize_header(h) }   # order preserved, duplicates included
  end
end

def normalized_body
  content = @raw_body.dup
  content.gsub!(/[ \t]+/, " ")      # WSP runs -> single SP
  content.gsub!(/ \r\n/, "\r\n")    # trailing WSP per line dropped (CRLF kept)
  content.gsub!(/[ \r\n]*\z/, "")   # trailing empty lines dropped
  content += "\r\n"                 # exactly one terminating CRLF
end

def signable_header_string
  (normalized_headers + [dkim_header_for_signing]).join("\r\n")   # "dkim-signature:v=1; …b=" lowercase, empty b=
end
```

**Flow:** normalize CRLF everywhere → select signable headers by fixed allowlist regex (case-insensitive, keeps original order AND repeated occurrences) → relaxed-normalize each (`key.downcase!`; unfold continuations; collapse WSP; strip trailing WSP; strip WSP after colon) → relaxed body canon → `bh=` base64 SHA256 → build tags `v=1; a=rsa-sha256; c=relaxed/relaxed; d=…; s=…; t=<utc epoch>; bh=…; h=<colon-joined names>; b=` → RSA-SHA256 over normalized headers + the lowercase self-reference line → base64 the signature into the emitted header.
**Invariant:** There is NO `l=` body-length tag and NO `x=` expiry — the whole (already rewritten) body is hashed. The signed byte string uses the *lowercase* header name form `dkim-signature:v=1; …` while the emitted header is `DKIM-Signature: v=1; …`; getting that asymmetry wrong breaks verification. Signing happens on the message AFTER tracking rewrites and spam-header appends (dequeuer ladder order), so the signature covers final delivered bytes.
**Probe:** `spec/lib/dkim_header_spec.rb` (golden-file harness over `spec/examples/dkim_signing/*.msg`: YAML frontmatter pins time/domain/key/bh/h/b; asserts exact folded output including `\r\n\t` continuation and 72-char b= wrapping).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "postal", query: "DKIM canonicalization header selection body hash", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the hand-rolled relaxed/relaxed canonicalization, the fixed allowlist-with-order-preserved header selection, and the fallback signing identity when a domain's DKIM isn't verified. Adapt the allowlist to your product surface (it is a policy choice, not an RFC mandate). Omit Postal's config namespaces; keep RFC 6376 §3.4.2/§3.4.4 step comments if porting the file. Caveat: no unit test drives the return-path-domain fallback branch — golden files all use the domain-OK path.
