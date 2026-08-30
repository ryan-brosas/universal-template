<!-- capsule-v2 -->
# Worker process loop — how do you run a multi-thread DB poller that drains in-flight work on SIGTERM?

**Source:** postal MIT `main@d038eaa8c763d3cafa797ccd6f773d53470bd336`; Codebase Memory `ext-postal`. **Question:** How does the worker interleave continuous queue polling with periodic maintenance tasks and still shut down gracefully mid-sleep?

## Worker::Process
**Path/Symbol:** `app/lib/worker/process.rb:Worker::Process` (JOBS :27, TASKS :35, initialize :48, receive_signal :84, shutdown_after_wait? :96, ensure_connection_pool_size_is_suitable :104, work :157, start_tasks_thread :190, run_tasks :216, run_task :242, capture_errors :284).
**Signature:** `initialize(thread_count: Config.worker.threads, work_sleep_time: 5, task_sleep_time: 60)`; `work(thread) → Boolean` (any job did work).
**Data Shape:** JOBS = `[ProcessQueuedMessagesJob, ProcessWebhookRequestsJob]` (continuous table watchers); TASKS = 9 scheduled maintenance classes; state = `@shutdown` flag + a closed-on-shutdown `IO.pipe`.

### Decisive source
```ruby
def receive_signal(signal)
  puts "Received #{signal} signal. Stopping when able."
  @shutdown = true
  @exit_pipe_write.close          # wakes EVERY sleeping thread instantly
end

def shutdown_after_wait?(wait_time)
  @exit_pipe_read.wait_readable(wait_time) ? true : false   # sleep that aborts on signal
end

def work(thread)
  completed_work = 0
  ActiveRecord::Base.connection_pool.with_connection do
    JOBS.each do |job_class|
      capture_errors do
        time = Benchmark.realtime { job_class.new(logger: logger).call }
        observe_prometheus_histogram :postal_worker_job_runtime, time, labels: {thread:, job:}
        completed_work += 1 if job.work_completed?      # per-job truthfulness flag
      end
    end
  end
  completed_work.positive?
end
```

**Flow:** trap INT/TERM → set flag + close pipe write-end → N work threads loop {run all JOBS inside one pooled connection → sleep 5 s unless signalled} → one tasks thread loops {acquire `WorkerRole` "tasks" → run due tasks → sleep 60 s} and on exit releases the role inside `with_connection` → main thread joins all threads. Tasks are stored as `ScheduledTask(name, next_run_after)` rows created on first sight with the class's declared schedule (`next_run_after` helpers: quarter-past/quarter-to hour, 3 AM), updated AFTER the run so failures re-run next tick.
**Invariant:** the pipe-closing trick is what makes shutdown fast — plain `sleep(5)` would delay every worker thread by up to its full sleep; `wait_readable(timeout)` returns the moment the write end closes. Every job/task body runs inside `capture_errors` (log + Sentry + error counter) — one exploding message never kills a thread or skips the sibling jobs in the same tick. Pool size is raised to `threads + 3` BEFORE threads start (each work thread holds a connection for the whole tick; the +3 covers the tasks thread, metrics, and headroom).
**Probe:** `spec/models/worker_role_spec.rb` (role lifecycle); deterministic probe executed this pass: `shutdown_after_wait?` returns true immediately when the write end closes (pipe semantics), pool sizing math `threads+3`. No upstream spec instantiates `Worker::Process` itself (it needs threads + DB); port with your own integration test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-postal", query: "Worker Process shutdown_after_wait start_work_thread run_tasks", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the exit-pipe interruptible sleep, the jobs-vs-scheduled-tasks split (pollers vs calendar-ish maintenance with persisted next-run rows), per-job `work_completed?` honesty flags feeding metrics, blanket `capture_errors` around each unit, and pool-sizing before thread spawn. Adapt the threading model to your runtime (asyncio/Go), the metric names, and ScheduledTask persistence. Omit Prometheus/klogger specifics.
