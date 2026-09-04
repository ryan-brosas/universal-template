<!-- capsule-v2 -->
# beam-api-boundary-funcs — Which BEAM powers are safe to hand to sandboxed JS, and how are they wrapped?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** What do the `__beam_*` handler implementations teach about exposing host capabilities (UUIDv7, PBKDF2, XML, process registry) to untrusted code?

## BeamAPI function surface seam
**Path/Symbol:** `lib/quickbeam/beam_api.ex:random_uuid_v7/1` (:48-73) + `uuid_atomics/0` (:75-87); `password_hash/verify` (:212-237); `xml_parse/1` (:203-210); `register_name/whereis` (:134-148).
**Signature:** all handlers take a LIST of decoded args and return plain terms; registered in runtime.ex @beam_handlers (`__beam_random_uuid_v7`, `__beam_password_hash`, ...).
**Data Shape:** UUID atomics pair `{counter, last_ms}` cached in persistent_term; password envelope `$pbkdf2-sha256$iterations$salt_b64$hash_b64`; XML → nested maps with `@attr` keys, `#text`, repeated children as lists.

### Decisive source
```elixir
ms = System.system_time(:millisecond)
{seq, rand_b} =
  if ms != :atomics.get(last_ms, 1) do
    :atomics.put(last_ms, 1, ms)
    rand_seq = :rand.uniform(4096) - 1
    :atomics.put(counter, 1, rand_seq)
    {rand_seq, :crypto.strong_rand_bytes(8)}
  else
    {:atomics.add_get(counter, 1, 1), :crypto.strong_rand_bytes(8)}
  end
<<a::32,b::16,c::16,d::16,e::48>> = <<ms::48, 0b0111::4, band(seq,0xFFF)::12,
                                       0b10::2, rand_b::62>>

# verify — constant-time compare, derived length from the STORED hash:
derived = :crypto.pbkdf2_hmac(:sha256, password, salt, iterations, byte_size(expected))
:crypto.hash_equals(derived, expected)

def register_name([name], _caller) when is_binary(name) do
  atom = String.to_atom(name)      # ← JS-controlled atom creation (documented hazard)
  Process.register(caller, atom); true
rescue _ -> false
```

**Flow:** UUIDv7 = ms timestamp + version nibble 0111 + 12-bit per-ms sequence (atomics; reset with fresh random on millisecond rollover) + variant 10 + random bits. Verify parses the envelope and re-derives with byte_size(expected) so truncated hashes fail safely. XML parse converts xmerl records into JSON-friendly maps, whitespace-collapsed text joined with single spaces.
**Invariant:** (1) The seq counter is shared node-wide via persistent_term+atomics — uniqueness holds across concurrent runtimes, monotonicity only within a millisecond bucket. (2) register_name uses String.to_atom (NOT to_existing_atom) — an untrusted caller can grow the atom table; rpc() by contrast uses to_existing_atom for both target atoms. whereis rescues ArgumentError → nil. Porters must decide which side of that line each capability sits on. (3) hash_equals + stored-length derivation is the security floor for the verify path. (4) xml_parse raises ArgumentError on malformed input (caught by dispatch → JS rejection), it never returns ok:false.
**Probe:** `grep -c 'String.to_atom' lib/quickbeam/beam_api.ex` → 1.
**Probe:** `grep -c 'to_existing_atom' lib/quickbeam/beam_api.ex` → 3.
**Probe:** direct test `test/core/beam_api_test.exs` pins this surface at the pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "random_uuid_v7 uuid_atomics pbkdf2 xml_parse register", limit: 10 });
```

## Verdict
Adopt the capability-wrapper discipline: allowlisted verbs, value-or-raise contracts, constant-time crypto compares, explicit atom-safety decisions per endpoint; adapt the verb set to your threat model. Coverage: beam_api.ex no_recorded_issue+metadata_match.
