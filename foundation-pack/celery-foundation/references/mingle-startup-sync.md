<!-- capsule-v2 -->
# Mingle startup sync — how do workers exchange clocks and revokes when joining a cluster?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** What state must a new worker import from its peers at startup, and what happens if it's alone?

## Mingle bootstep
**Path/Symbol:** `celery/worker/consumer/mingle.py:Mingle` (:12-75); reply handlers consumed by Gossip; clock primitive `celery.app.base` Lamport clock (`adjust/forward`).
**Signature:** `sync(c)` → `send_hello(c)` via `app.control.inspect(timeout=1.0, connection=c.connection).hello(c.hostname, our_revoked._data)` → per-reply `sync_with_node(c, clock=None, revoked=None)`.
**Data Shape:** hello replies: `{nodename: {ok, clock, revoked, ...}}`; own reply popped before counting; transport-gated to `{amqp, redis, gcpubsub}`.

### Decisive source
```python
# celery/worker/consumer/mingle.py:41-56
def sync(self, c):
    info('mingle: searching for neighbors')
    replies = self.send_hello(c)
    if replies:
        info('mingle: sync with %s nodes',
             len([reply for reply, value in replies.items() if value]))
        [self.on_node_reply(c, nodename, reply)
         for nodename, reply in replies.items() if reply]
        info('mingle: sync complete')
    else:
        info('mingle: all alone')            # first worker: valid outcome

def on_clock_event(self, c, clock):
    c.app.clock.adjust(clock) if clock else c.app.clock.forward()
```

**Flow:** runs after Events in the consumer blueprint (requires=(Events,)) unless `-without-mingle` or incompatible transport → broadcast hello carrying OUR logical clock and revoked list → each live peer replies with its clock + revoked set → for every reply: adjust our Lamport clock to max(theirs), merge their revoked ids into the local LimitedSet → per-node failures are logged and skipped (exception handler), never fatal.
**Invariant:** (1) Clock adjustment uses `adjust(other)` (take the max) — forwarding unconditionally would desync Lamport ordering used by gossip elections. (2) Revoked-task knowledge MUST be imported or a new worker re-executes tasks revoked cluster-wide moments earlier. (3) "All alone" is a normal path, not an error — the first worker must start. (4) Reply timeout is 1.0s so a hung peer can't stall startup beyond that window.
**Probe:** `t/unit/worker/test_consumer.py::test_Mingle` (:1430+) pins send_hello/sync_with_node/clock-adjust behavior.
**Retrieve:**
```json
{"project":"ext-celery","query":"Mingle send_hello sync_with_node clock revoked","limit":5,"detail":"ids"}
```
## Verdict
Adopt: bounded-timeout hello round, max-clock adjust, revoked-set import, alone-is-fine semantics. Adapt inspect-over-connection to your control channel. Omit transport compatibility gating if your transport always supports broadcast replies.
