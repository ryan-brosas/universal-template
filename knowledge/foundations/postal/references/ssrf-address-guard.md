<!-- capsule-v2 -->
# SSRF address guard — how do you fetch attacker-supplied URLs without letting them reach internal networks?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `ext-postal`. **Question:** How does Postal stop webhook/HTTP-endpoint URLs from hitting loopback, RFC1918, or cloud-metadata addresses — including DNS-rebinding races?

## Postal::HTTP + AddressGuard
**Path/Symbol:** `lib/postal/http.rb:request` (18–104; guard call :56, pin :62, rescue ladder :77–102); `lib/postal/http/address_guard.rb` (BLOCKED_RANGES :19–47, safe_connect_address :95–133, resolve :136–147, family_reachable? :154–161, blocked? :163–175, allowlist :177–202).
**Signature:** `AddressGuard.safe_connect_address(host) → String(ip)` (raises `BlockedDestinationError` | `SocketError`); `Postal::HTTP.request(method, url, options) → {code:, body:, headers:, secure:}` with negative codes for failures.
**Data Shape:** BLOCKED_RANGES = 11 IPv4 + 6 IPv6 CIDRs incl. `169.254.0.0/16` (metadata), `100.64.0.0/10` (CGNAT), `::ffff:0:0/96` (v4-mapped). Allowlist config entries parse as IP/CIDR → matched against resolved address; otherwise matched case-insensitively against the HOSTNAME.

### Decisive source
```ruby
# http.rb — resolve ONCE and pin: the socket cannot be re-targeted by a second DNS lookup
connect_address = AddressGuard.safe_connect_address(uri.host)
connection = Net::HTTP.new(uri.host, uri.port)
connection.ipaddr = connect_address      # DNS rebinding race killed here
...
rescue BlockedDestinationError => e   { code: -4 }   # policy block
rescue OpenSSL::SSL::SSLError         { code: -3 }   # invalid certificate
rescue Resolv::ResolvError, SocketError, SystemCallError, EOFError => e
                                      { code: -2 }   # connectivity
rescue Timeout::Error                 { code: -1 }   # timed out after Ns

# address_guard.rb — fail closed on ANY bad address, then filter by reachable family
addresses.each do |address|
  next unless blocked?(address)
  raise BlockedDestinationError, "Destination '#{@host}' (#{address}) is not permitted"
end
usable = addresses.select { |a| family_reachable?(a) }
raise SocketError, "'#{@host}' only resolves to addresses this server cannot reach" if usable.empty?
(usable.find(&:ipv4?) || usable.first).to_s        # prefer IPv4 for predictability

def blocked?(address)
  return false if allowlisted?(address)
  if address.ipv6? && address.ipv4_mapped?          # ::ffff:10.0.0.5 must be checked as IPv4…
    mapped = address.native
    return true if mapped.ipv4? && BLOCKED_RANGES.any? { |r| r.include?(mapped) }
  end                                               # …else it slips past the v4 ranges
  BLOCKED_RANGES.any? { |range| range.include?(address) }
end
```

**Flow:** host → IP literal short-circuit (`IPAddr.new` succeeds ⇒ no DNS at all) or `Resolv.getaddresses` (garbage records silently dropped) → ANY blocked address raises (defeats mixed public+private DNS tricks — the request dies even if a "clean" address is available) → filter to families this machine can actually route (loopback-excluded local interface scan, memoized; v4 defaults true unless host is v6-only) → pick v4-first → caller pins `Net::HTTP#ipaddr=` so connect() uses the validated byte-for-byte address.
**Invariant:** check-then-pin must stay paired — validating without pinning leaves the rebinding hole, pinning without validation just moves it. Allowlist evaluation happens INSIDE `blocked?` so an allowed entry overrides every range check for that host/CIDR. Failures are VALUES (negative codes), never exceptions crossing into callers like HTTPSender/WebhookDeliveryService — which is why they classify `code < 0` as SoftFail+connect_error.
**Probe:** `spec/lib/postal/http/address_guard_spec.rb:49–190` (blocked raises; one-of-two blocked raises; v4-preferred; v6-only host w/o v6 support ⇒ SocketError; CIDR/exact-IP/hostname allowlists pass through); `spec/lib/postal/http_spec.rb:11–77` (no request made to blocked hosts via WebMock; pin asserted on Net::HTTP instance). Deterministic probe executed this pass re-derived the blocklist incl. the v4-mapped bypass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-postal", query: "safe_connect_address BlockedDestinationError blocked allowlist", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt resolve→block-if-ANY-bad→family-filter→pin, the v4-mapped-v6 recheck, hostname-vs-CIDR dual allowlist semantics, and negative-code error values for outbound HTTP. Adapt the range list to your environment (add your own metadata ranges), and swap `Net::HTTP#ipaddr=` for your HTTP client's equivalent (e.g. custom dialer pinning).
