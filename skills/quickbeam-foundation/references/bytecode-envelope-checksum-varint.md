<!-- capsule-v2 -->
# bytecode-envelope-checksum-varint — How do you accept a foreign engine's serialized bytecode without trusting a single byte of it?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `quickbeam`. **Question:** What stands between raw QuickJS bytecode bytes and a verified `%Program{}`?

## Envelope integrity + decode-limit seam
**Path/Symbol:** `lib/quickbeam/vm/bytecode/checksum.ex` (38L whole) — `verify/1` (:11-15), `checksum_words/2` (:21-37), `@factor 0x9E370001`; `lib/quickbeam/vm/bytecode/decoder.ex:decode/1` (:52-73) with caps `@max_input_bytes 16MiB / @max_nesting_depth 128 / @max_entries 100_000 / @max_function_bytecode_bytes 4MiB` (:42-45); varint contract per `test/vm/bytecode/varint_test.exs` (31L whole).
**Signature:** `Checksum.verify(binary) :: :ok | {:error, :unexpected_end | :checksum_mismatch}`; `Decoder.decode(binary) :: {:ok, Program.t()} | {:error, term()}`.
**Data Shape:** envelope = `<<version_byte, expected::little-u32, payload::binary>>`; Program stamps `version`, `fingerprint` (ABI), `bytecode_digest` (sha256 of full binary), `atoms`, root function.

### Decisive source
```elixir
def verify(<<_version, expected::little-unsigned-32, payload::binary>>) do
  if calculate(payload) == expected, do: :ok, else: {:error, :checksum_mismatch}
end

defp checksum_words(<<word::little-unsigned-32, rest::binary>>, checksum)
     when byte_size(rest) > 0 do
  checksum = band(checksum + word, @mask)
  checksum_words(rest, band(checksum * @factor, @mask))
end
```
```elixir
def decode(data) when is_binary(data) and byte_size(data) > @max_input_bytes,
  do: {:error, {:limit_exceeded, :bytecode_bytes, byte_size(data)}}

def decode(data) when is_binary(data) do
  with {:ok, version, rest} <- LEB128.read_u8(data),
       :ok <- validate_version(version),
       :ok <- Checksum.verify(data),
       ...
```

**Flow:** bytes → size gate BEFORE any parse → version byte validated → QuickJS-compatible checksum over LE32 words (factor 0x9E370001; 1–3 trailing bytes folded via masked shift-or tail) → atom table → object tree with nesting/entry/per-function caps enforced during recursion → trailing-bytes check (`ensure_consumed`) → `%Program{}` stamped with sha256 bytecode_digest + ABI fingerprint — exactly the fields the compiler Contract later hashes into artifact keys.
**Invariant:** (1) Corruption is detected before interpretation: the checksum covers the payload and mismatches are typed (`:checksum_mismatch`), never silent. (2) Every resource is bounded pre-parse or mid-recursion (total bytes, nesting depth, entry count, per-function size) so a hostile blob costs bounded work — mirroring the decoder's claim to match `JS_ReadObject*` byte-for-byte while adding limits QuickJS itself lacks in-process. (3) Varint layer rejects unterminated LEB128 (`:bad_leb128`) and >32-bit values (`:integer_overflow`); ZigZag signed and fixed-width LE u32 readers are separate entry points so callers cannot mix encodings (varint_test.exs asserts each). (4) The digest stamped at decode time binds downstream caches: change one input byte and every compiler artifact key derived from this program changes.
**Probe:** `grep -c '0x9E370001' lib/quickbeam/vm/bytecode/checksum.ex` → 1 (:6, observed).
**Probe:** `grep -n 'checksum_mismatch\|little-unsigned-32' lib/quickbeam/vm/bytecode/checksum.ex` → lines 10,11,12,21 (observed).
**Probe (test):** varint_test.exs "rejects unterminated and wider-than-32-bit encodings" (:21-30).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "QuickJS bytecode checksum envelope verify little endian payload", limit: 5 });
```
(observed rank-1: bytecode.checksum.verify checksum.ex:11-15; rank-2: decoder_test.bytecode_envelope test fixture :242-245)

## Verdict
Adopt for importing ANY foreign serialized IR (bytecode, wasm modules, protobuf trees from untrusted peers): verify-first envelope checksum, typed truncation/corruption errors, resource caps before/during parse, and digest stamping that downstream caches key on. Adapt word width/endian/factor to your producer format. Omit nothing here — the caps are the security boundary. Coverage: cited paths no_recorded_issue+metadata_match @ gen 2026-08-25T19:58:40Z.
