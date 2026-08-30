<!-- capsule-v2 -->
# Artifact digest revalidation — how do you close the TOCTOU window between compiling a module binary and loading it into the code server?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** What stops an artifact from being substituted or corrupted between emission and installation?

## Connected graph-selected seam
**Path/Symbol:** `lib/quickbeam/vm/compiler/code/artifact.ex:Artifact.new/2` + `validate/1` (lines 17-43), consumed by `lifecycle.ex:install/2:21`.
**Signature:** `new(module(), binary()) :: {:ok, %Artifact{module:, binary:, digest:}} | {:error, term()}`; `validate(t()) :: :ok | {:error, term()}`.
**Data Shape:** `%Artifact{}` = slot module + BEAM binary + SHA-256 digest stamped at construction; size cap `@max_binary_bytes 8 MiB` enforced at BOTH construction and validation (`{:compiler_resource_limit, :module_bytes, size, max}`).

### Decisive source
```elixir
def new(module, binary) when is_atom(module) and is_binary(binary) do
  if byte_size(binary) <= @max_binary_bytes do
    {:ok, %__MODULE__{module: module, binary: binary, digest: digest(binary)}}
  else
    {:error, {:compiler_resource_limit, :module_bytes, byte_size(binary), @max_binary_bytes}}
  end
end

def validate(%__MODULE__{binary: binary, digest: expected}) when is_binary(binary) do
  cond do
    byte_size(binary) > @max_binary_bytes -> {:error, {:compiler_resource_limit, ...}}
    expected != digest(binary) -> {:error, :artifact_digest_mismatch}
    true -> :ok
  end
end

defp digest(binary), do: :crypto.hash(:sha256, binary)
```

**Flow:** emit → `Artifact.new` stamps the digest → artifact may travel through pool state (cache slots, lease handoff) → at install time `Lifecycle.install/2` re-runs `Artifact.validate/1` BEFORE `Import.validate/1` and BEFORE `:code.load_binary/3`, so only the exact bytes that were hashed can ever be loaded.
**Invariant:** no code path loads a generated binary whose current bytes do not match its construction-time digest; a tampered struct cannot install. The install pipeline order matters: module-name match → artifact validate → import allowlist → empty-slot check → load.
**Probe:** `test/vm/compiler/code_test.exs:105-107`: emits a valid artifact, then `tampered = %{artifact | digest: <<0::256>>}; assert {:error, :artifact_digest_mismatch} = Lifecycle.install(module, tampered)`. Probe executed: grep test tree → `artifact_digest_mismatch` ×1 (line 107).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "artifact digest revalidate binary size before install", limit: 5 });
// observed: code.artifact.digest #1 (artifact.ex:45); below it ts crypto-subtle and contract.digest noise.
```

## Verdict
Adopt stamp-at-construction + verify-immediately-before-load with sha256 over the raw binary; adapt the 8 MiB cap to your host's realistic generated-module ceiling; omit nothing — dropping the pre-load revalidation reintroduces the substitution window even if emission validated once. Coverage: both cited paths returned `no_recorded_issue` + `metadata_match`.
