<!-- capsule-v2 -->
# Gossip consensus election — how do peers pick a leader without a coordinator?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** How do workers elect a leader for a topic (e.g. "who runs this singleton task") using only event broadcasts and a logical clock?

## Gossip bootstep
**Path/Symbol:** `celery/worker/consumer/gossip.py:Gossip(ConsumerStep)` (:24-206); election handlers `on_elect` (:96-107), `on_elect_ack` (:115-136); liveness `periodic` (:172-180); mingle sync twin `celery/worker/consumer/mingle.py:Mingle.sync`.
**Signature:** `election(id, topic, action=None)`; consensus state `consensus_requests = defaultdict(list)` (heap per id), `consensus_replies = {}`; candidate identity `full_hostname = hostname.pid`.
**Data Shape:** events `worker.elect {id, clock, hostname, pid, topic, action, cver}` and `worker.elect.ack {id}`; candidates heap-ordered by `(clock, f'{hostname}.{pid}')`; transport-gated to amqp/redis.

### Decisive source
```python
# celery/worker/consumer/gossip.py:96-105 — every peer acks with its own vote
def on_elect(self, event):
    (id_, clock, hostname, pid, topic, action, _) = self._cons_stamp_fields(event)
    heappush(
        self.consensus_requests[id_],
        (clock, f'{hostname}.{pid}', topic, action))
    self.dispatcher.send('worker-elect-ack', id=id_)
```
```python
# :115-135 — quorum reached: lowest (clock, node) wins
if len(replies) >= len(alive_workers):
    _, leader, topic, action = self.clock.sort_heap(
        self.consensus_requests[id])
    if leader == self.full_hostname:
        info('I won the election %r', id)
        handler = self.election_handlers[topic]   # e.g. 'task': call_task
        handler(action)
    self.consensus_requests.pop(id, None)
    self.consensus_replies.pop(id, None)
```

**Flow:** any worker calls `election(id, topic)` → broadcasts worker-elect → each receiver pushes the CANDIDATE (not itself) onto its local heap and immediately acks → when an observer has collected acks from all alive workers it pops the min by `(clock, hostname.pid)` — lowest Lamport clock wins, hostname.pid breaks ties deterministically → only the winner executes its topic handler → state cleaned. Neighbor discovery/clock seeding comes from Mingle at startup (`inspect.hello` exchanging clock + revoked sets). Liveness: `periodic()` timer evicts workers whose heartbeat went stale (`state.alive`) firing `on_node_lost`.
**Invariant:** (1) Votes are pushed under the CANDIDATE's clock value — comparing your own clock would corrupt ordering. (2) Quorum is computed against `alive_workers()` at ack time; partitions can elect different leaders (documented best-effort). (3) The consumer subscribes `routing_key='worker.#'` with no_ack and IGNORES `task.*` routing keys explicitly (redis fanout quirk #1882). (4) Handler exceptions never propagate into the event loop.
**Probe:** smoke-level behavior pinned in `t/smoke/tests/test_gossip.py`; unit surface via `t/unit/app/test_control.py::test_election`-adjacent Panel tests and mingle tests in `t/unit/worker/test_consumer.py::test_Mingle` (:1430).
**Retrieve:**
```json
{"project":"ext-celery","query":"Gossip on_elect on_elect_ack sort_heap alive_workers","limit":5,"detail":"ids"}
```
## Verdict
Adopt: clock-ordered candidate heaps, immediate-ack quorum counting, deterministic tie-break, winner-only execution. Adapt event broadcast transport and Lamport clock implementation. Omit gossip entirely if you have a real coordination service — this is broker-only best-effort.
