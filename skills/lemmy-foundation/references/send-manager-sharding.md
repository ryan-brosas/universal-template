<!-- capsule-v2 -->
# SendManager instance sharding — how do you scale outbound dispatch across processes without coordination?

**Source:** lemmy AGPL-3.0 `main@439734dd638a2c06a2f907beab7dcf4646e88f86`; Codebase Memory `ext-lemmy`. **Question:** How does the fleet of per-instance workers get created, health-checked, and partitioned across N OS processes with zero shared state?

## SendManager reconcile loop
**Path/Symbol:** `crates/apub/send/src/lib.rs:SendManager` (`do_loop` :100–170, `cancel` :172–190); restartable task wrapper `crates/apub/send/src/util.rs:CancellableTask` (:83–131).
**Signature:** `run(opts: Opts, context: FederationConfig<LemmyContext>, config: FederationWorkerConfig) -> CancellableTask` where `Opts { process_count: i32, process_index: i32 /* 1-based */ }`.
**Data Shape:** `workers: HashMap<InstanceId, CancellableTask>`; reconciliation source query `Instance::read_federated_with_blocked_and_dead(pool)` returning `(instance, allowed, is_dead)` triples; consts `WORKER_EXIT_TIMEOUT = 30 s`, `INSTANCES_RECHECK_DELAY = 60 s` prod / 5 s debug (:24–28).

### Decisive source
```rust
// lib.rs:115-133 — static modulo sharding: each process owns instance ids where
// id % process_count == (process_index - 1). No locks, no leases, no overlap.
if instance.domain == local_domain { continue; }
if instance.id.inner() % self.opts.process_count != process_index { continue; }
let should_federate = allowed && !is_dead;
if should_federate {
  if self.workers.contains_key(&instance.id) {
    continue;                                   // idempotent reconcile: already running
  }
  self.workers.insert(instance.id, CancellableTask::spawn(WORKER_EXIT_TIMEOUT, move |stop| {
    InstanceWorker::init_and_loop(instance, context.clone(), cfg, stop, stats_sender.clone())
  }));
} else if !should_federate && let Some(worker) = self.workers.remove(&instance.id) {
  worker.cancel().await?;                       // blocked or dead ⇒ tear that peer's worker down
}

// util.rs:99-107 — CancellableTask: an errored inner loop is RESTARTED forever unless cancelled;
// graceful cancel = token + bounded wait, then abort
loop {
  let res = task(stop2.clone()).await;
  if stop2.is_cancelled() { return; }
  tracing::warn!("task exited, restarting: {res:?}");
}
```

**Flow:** every recheck interval, enumerate candidate remote instances → shard-filter by modulo → spawn a worker for newly-federable peers not yet in the map → cancel+remove workers whose peer became blocked/dead → on shutdown, drop the stats sender first (closing the stats channel), then cancel ALL worker tasks CONCURRENTLY (`join_all`) so their save-state-on-exit paths run together within the 30 s grace. `CancellableTask` converts any internal error exit into an automatic restart, so a transient DB blip never permanently kills one peer's queue.
**Invariant:** at most ONE worker per instance fleet-wide — guaranteed by pure function `instance_id % process_count`, not by distributed locking; and worker liveness is self-healing (restart-on-error) while membership follows DB truth each tick. Local domain is always excluded.
**Probe:** `crates/apub/send/src/lib.rs` tests `test_send_manager_processes` (:294–314 — three processes × index 1..3 produce exactly three disjoint single-worker sets), `test_send_manager_blocked` (:319+, blocklist removes the peer), `test_send_manager_allowed` (:341+, allowlist keeps only allowed), `test_send_manager_dead` (:362+, stale `updated_at` marks dead).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lemmy", name_pattern: "SendManager", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt deterministic key-sharding over the work entity's primary key for stateless horizontal scale-out, the map-reconcile loop (spawn missing / cancel removed), and the token-cancel-with-deadline restartable task wrapper. Adapt shard width to your deployment (the same math shards threads or pods) and replace the allow/blocklist predicate with your policy source. Omit the FederationConfig plumbing specifics.
