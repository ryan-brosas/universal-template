<!-- capsule-v2 -->
# vm-event-loop-drive — How do you await a JS promise to completion without polling?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** What is the event-loop state machine that drains microtasks, host replies, and the final promise?

## owner-local drive loop seam
**Path/Symbol:** `lib/quickbeam/vm/runtime.ex:drive_with/2` (:64-92), `await_final_promise/3` (:94-102), `drive_event_loop/3` (:121-133), `receive_host_reply/3` (:201-209).
**Signature:** interpreter returns one of `{:ok, %PromiseReference{}, execution}` | `{:ok|:error, value, execution}` | `{:suspended, %Continuation{}}` | `{:idle, execution}`; jobs are tuples like `{:run_reaction,...}`, `{:settle_promise,...}`, `{:resume_coroutine,...}`.
**Data Shape:** `execution` owns queues `jobs` (microtasks), `sync_jobs`, map `operations` (outstanding async host ops); final result = settled state of the eval's root PromiseReference.

### Decisive source
```elixir
defp drive_event_loop(final_promise, execution, finish) do
  case :queue.out(execution.jobs) do
    {{:value, job}, jobs} ->
      run_job(job, final_promise, %{execution | jobs: jobs}, finish)
    {:empty, _jobs} when map_size(execution.operations) > 0 ->
      receive_host_reply(final_promise, execution, finish)   # BLOCKS here
    {:empty, _jobs} ->
      finish.({:error, {:promise_deadlock, final_promise.id}, execution})
  end
end

defp receive_host_reply(final_promise, execution, finish) do
  receive do
    {:quickbeam_vm_host_reply, operation, result} ->
      case Async.settle_host_reply(execution, operation, result) do
        {:ok, execution} -> await_final_promise(final_promise, execution, finish)
        :stale -> receive_host_reply(final_promise, execution, finish)  # ignore, keep waiting
      end
  end
end
```

**Flow:** start → if result is a pending final promise: run sync_jobs first → then loop {drain one job → re-check; no jobs but ops outstanding → blocking receive on exactly the host-reply message; nothing runnable and nothing outstanding ⇒ deadlock error} → settle maps fulfilled/rejected to ok/error with JSError translation.
**Invariant:** (1) NO polling and NO timeout in this loop — progress is event-driven; the deadlock error fires only when a promise can never settle (ops==0). (2) Stale host replies (from cancelled operations) are consumed and IGNORED without spinning. (3) finish_final cancels remaining async operations (`Async.cancel_operations`) so a failed eval doesn't leak later replies into the caller's mailbox. (4) The whole machine lives in the OWNER process — no GenServer involved — which is what makes per-eval isolation cheap.
**Probe:** `grep -c 'promise_deadlock' lib/quickbeam/vm/runtime.ex` → 1.
**Probe:** `grep -c 'settle_host_reply' lib/quickbeam/vm/runtime.ex` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "drive event loop jobs operations host reply deadlock", limit: 10 });
```

## Verdict
Adopt the three-way loop (jobs / blocking-reply / deadlock) as the reference no-polling await for embedded interpreters; adapt job tuple shapes; keep stale-reply tolerance and terminal cancel_operations. Coverage: runtime.ex (vm) no_recorded_issue+metadata_match; direct tests test/vm/runtime/{promise_test,async_test}.exs exercise fulfillment chains and host-reply correlation at the pin.
