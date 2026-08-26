<!-- capsule-v2 -->
# vm-pin-store-lease — How do you share one compiled program across concurrent evaluations safely?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** What does the pin/checkout/checkin lifecycle guarantee about program immutability and identity?

## Program Store lease seam
**Path/Symbol:** `lib/quickbeam/vm.ex:pin/1` (:175-189) + moduledoc capacity contract (:20-26); `lib/quickbeam/vm/runtime/engine.ex:pinned_lease/1` (:254-259), `evaluate_pinned_caller` (:261-266), `after Store.checkin(lease)` (:79-83).
**Signature:** `pin(%Program{}) :: {:ok, %Pinned{}} | {:error, :pinned_program_capacity | :pinned_program_unavailable}`; `unpin/1`; engine path `Store.checkout(pinned) → fetch(lease) → Verifier.verify_identity(program) → evaluate → Store.checkin(lease)` in an `after` clause.
**Data Shape:** Default store = EIGHT fixed slots; serialized bytecode ≤ 2 MiB; decoded external-term residency ≤ 32 MiB per program; total residency ≤ 128 MiB; pins idempotent BY PROGRAM IDENTITY (not refcounted).

### Decisive source
```elixir
def eval(%Pinned{} = pinned, opts, request) do
  with {:ok, options} <- evaluation_options(opts),
       {:ok, lease} <- pinned_lease(pinned) do
    options = Map.put(options, :request, request)
    try do
      case options.isolation do
        :caller  -> evaluate_pinned_caller(lease, options)
        :process -> eval_isolated_pinned(lease, options)
      end
    after
      Store.checkin(lease)
    end
  end
end

defp evaluate_pinned_caller(lease, options) do
  with {:ok, program} <- Store.fetch(lease),
       :ok <- Verifier.verify_identity(program),   # ← re-verify at USE time
       do: evaluate(program, options)
end
```

**Flow:** pin verifies + stores once, returns lightweight handle (same identity ⇒ same handle) → each eval checks out a lease → fetches and RE-VERIFIES the program's identity → evaluates against a copy-fresh heap → checkin in `after` so crashes still release.
**Invariant:** (1) Identity is content-based (`Identity.put`, source_digest sha256) — two pins of equal programs are idempotent, therefore ONE lifecycle owner must coordinate unpin (no refcount). (2) verify_identity at use time closes the TOCTOU gap between pin and eval. (3) Fixed slots mean exhaustion is a NORMAL error (:pinned_program_capacity via :unavailable / :retiring states) — never implicit eviction. (4) The app-supervised store restores valid slots after ITS restart, but callers must still handle stale-handle errors on their own restarts.
**Probe:** `grep -c 'pinned_program_capacity' lib/quickbeam/vm.ex` → 2.
**Probe:** `grep -c 'verify_identity' lib/quickbeam/vm/runtime/engine.ex` → 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "Store checkout checkin lease verify_identity", limit: 10 });
```

## Verdict
Adopt the fixed-slot immutable-program store with lease+identity-recheck for sharing compiled artifacts across sandboxed evals; adapt slot counts/limits to your memory budget; keep single-owner unpin semantics or add refcounting consciously. Coverage: vm.ex/engine.ex no_recorded_issue+metadata_match.
