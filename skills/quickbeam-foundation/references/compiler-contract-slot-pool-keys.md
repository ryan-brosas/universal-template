<!-- capsule-v2 -->
# compiler-contract-slot-pool-keys — How do you cache unbounded compiled artifacts on the BEAM without blowing up the atom table?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `quickbeam`. **Question:** How are generated-module identities made deterministic AND atom-table-safe for attacker-controlled program counts?

## Fixed-slot identity seam
**Path/Symbol:** `lib/quickbeam/vm/compiler/contract.ex` — `@pool_modules` Slot00..Slot31 (:18-51), `program_identity/1` (:75-89), `artifact_key_from_identity/3` (:137-157), `artifact_function_identity/1` (:162-180), `digest/1` (:182-185).
**Signature:** `program_identity(Program.t()) :: {:ok, 32-byte binary}`; `artifact_key(program|identity, Function.t(), profile: | region_entry: | region_preferred:) :: {:ok, binary()} | {:error, term()}`.
**Data Shape:** namespace payload = `{contract_version, runtime_abi_version, version, fingerprint, bytecode_digest, source_digest, atoms}`; function key payload = `{namespace, function_identity, profile, region_entry, region_preferred}`.

### Decisive source
```elixir
defp artifact_function_identity(%Function{} = function) do
  constants =
    Enum.map(function.constants, fn
      %Function{id: id} -> {:function_constant, id}
      value -> value
    end)

  %{
    function
    | atoms: nil,
      constants: constants,
      filename: nil,
      line_num: 1,
      col_num: 1,
      pc2line: <<>>,
      source: <<>>,
      source_positions: nil
  }
end

defp digest(value) do
  binary = :erlang.term_to_binary(value, [:deterministic])
  :crypto.hash(:sha256, binary)
end
```

**Flow:** verified Program → SHA-256 namespace over its immutable digests → per-function key = hash of {namespace, scrubbed function identity, profile knobs} → Pool maps key → one of exactly 32 fixed module atoms (`QuickBEAM.VM.Compiler.Slot00..Slot31`). Region admission uses a separate cheap key space tagged `:region_admission` validated against the same 32-byte width.
**Invariant:** (1) Module names come from a compile-time closed set — no matter how many programs/functions/regions are compiled, `:erlang.system_info(:atom_count)` never grows (contract_test warms then measures across 10,000 derivations and asserts zero growth). (2) Keys depend only on SEMANTICS: debug-only fields (filename, line_num, col_num, pc2line, source text, source_positions) are scrubbed and provably do not change the key, while fingerprint / stack_size / source_digest / atoms do. (3) Determinism comes from `term_to_binary(..., [:deterministic])`, so keys are reproducible across nodes/restarts — usable as persistent cache keys. (4) Unknown options, unsupported profiles, negative region entries all fail with typed errors rather than being silently dropped from the key.
**Probe:** `grep -c 'Slot' lib/quickbeam/vm/compiler/contract.ex` → 33 observed Slot-name occurrences in @pool_modules (Slot00–Slot31 = 32 modules).
**Probe:** `grep -n ':deterministic' lib/quickbeam/vm/compiler/contract.ex` → line 183 (observed).
**Probe (test):** contract_test.exs "artifact identities cover the program fingerprint and immutable function" asserts `debug_only_key == key` while four semantic mutations each change it (:54-100).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "deterministic artifact key sha256 module atom slot pool", limit: 5 });
```
(observed rank-1..4: compiler.artifact_key compiler.ex:200-205, contract.artifact_key :114-115, contract.artifact_key_bytes :63, contract.artifact_key_from_identity :159-160)

## Verdict
Adopt fixed-atom-slot + deterministic-hash identities whenever dynamically-generated module/class names could be attacker-inflated (BEAM atoms, JVM class loaders, JS eval registries). Adapt the payload fields to whatever makes an artifact semantically unique in your host. Omit the region_admission twin if you have no sub-unit hot entries. Coverage: cited path no_recorded_issue+metadata_match @ gen 2026-08-25T19:58:40Z.
