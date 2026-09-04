<!-- capsule-v2 -->
# script-load-handshake — How does start_link guarantee the startup script finished before the caller proceeds?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** How do you return a child pid only after async native initialization succeeds, without blocking init?

## Caller-ref handshake seam
**Path/Symbol:** `lib/quickbeam/runtime.ex:start_link/1` (:29-61), `init/2` tail (:325-334), `handle_continue({:load_script,...})` (:337-347), `await_ref_with_callbacks/3` (:373-390).
**Signature:** `start_link(opts) :: {:ok, pid} | {:error, reason}`; opts carry hidden `:__caller__` (caller pid) and `:__ref__` (`make_ref()`).
**Data Shape:** With `script:` in opts, init returns `{:ok, state, {:continue, {:load_script, opts, caller, ref}}}`; completion is signaled by `send(caller, {ref, :script_loaded})` or `{ref, {:script_error, reason}}`; failure also `{:stop, :normal, state}`.

### Decisive source
```elixir
{:ok, pid} = GenServer.start_link(__MODULE__, opts, ...)
if Keyword.has_key?(opts, :script) do
  mon = Process.monitor(pid)
  receive do
    {^ref, :script_loaded} -> Process.demonitor(mon, [:flush]); {:ok, pid}
    {^ref, {:script_error, reason}} -> Process.demonitor(mon, [:flush]); {:error, reason}
    {:DOWN, ^mon, :process, ^pid, reason} -> {:error, reason}
  after
    30_000 -> {:error, :script_timeout}
  end
else
  {:ok, pid}
end
```

**Flow:** start_link embeds caller+make_ref into opts → GenServer starts normally (init installs handlers/builtins fast) → continue evaluates the script via Native.eval → while waiting, `await_ref_with_callbacks/3` re-enters on `{:beam_call,...}` messages so a startup script that calls back into Elixir still makes progress → success/error/DOWN resolves the caller.
**Invariant:** (1) The ref pattern-match makes stale or foreign messages harmless. (2) The DOWN clause covers script crash during load — caller gets an error, not a hang. (3) The 30 s cap bounds even an infinite-loop startup script. (4) beam_call re-entry during await means handler execution works BEFORE start_link returns — porters who block without pumping callbacks deadlock on scripts using Beam.call at import time. (5) Same 30 s constant appears in Context.load_script and sync NIF awaits — it is the project-wide native-await budget.
**Probe:** `grep -c '__caller__' lib/quickbeam/runtime.ex` → 2.
**Probe:** `grep -c 'script_loaded' lib/quickbeam/runtime.ex` → 2.
**Probe:** `grep -c '30_000' lib/quickbeam/context.ex` → 2 (load_script + sync_load_bytecode).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "script loaded continue load_script timeout", limit: 10 });
```

## Verdict
Adopt the ref-tagged handshake + monitor + bounded await as the canonical "async-init child" recipe; adapt timeouts and message shapes; omit the beam_call pump if your startup scripts cannot call hosts. Coverage: runtime.ex no_recorded_issue; direct tests test/core/supervision_test.exs pin supervisor semantics around this seam.
