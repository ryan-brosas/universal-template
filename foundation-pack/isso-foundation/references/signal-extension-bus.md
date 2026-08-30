<!-- capsule-v2 -->
# Signal extension bus — how do notification backends subscribe without imports?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What is the full lifecycle event set and the subscription protocol?

## Iterable-of-pairs Signal
**Path/Symbol:** `isso/ext/__init__.py:Signal` (lines 6–16); wiring `isso/__init__.py:Isso.__init__` (lines 107–119); emitters in `isso/views/comments.py`.
**Signature:** `Signal(*subscribers)`; each subscriber implements `__iter__` yielding `(signal_name, handler)` pairs; `signal(origin, *args, **kwargs)` fans out.
**Data Shape:** events: `comments.new:new-thread(thread)`, `comments.new:before-save(thread, data)`, `comments.new:guard(reason)`, `comments.new:after-save(thread, rv)`, `comments.new:finish(thread, rv)`, `comments.edit(rv)`, `comments.delete(id)`, `comments.activate(thread, item)`.

### Decisive source
```python
class Signal(object):
    def __init__(self, *subscriber):
        self.subscriptions = defaultdict(list)
        for sub in subscriber:
            for signal, func in sub:
                self.subscriptions[signal].append(func)

    def __call__(self, origin, *args, **kwargs):
        for subscriber in self.subscriptions[origin]:
            subscriber(*args, **kwargs)
```
```python
# SMTP backend:
def __iter__(self):
    yield "comments.new:after-save", self.notify_new
    yield "comments.activate", self.notify_activated
```

**Flow:** app assembly instantiates Stdout always, SMTP when `[general] notify` contains smtp OR reply-notifications is on → Signal collects pairs → views emit at each lifecycle point. Emission order follows registration order; handlers run INLINE (no queue).
**Invariant:** The bus is synchronous and exception-UNSAFE — a raising subscriber propagates into the request. Porters wanting isolation must wrap handler calls. Note `before-save` receives the MUTABLE data dict (guard/auto-approve mutations are visible downstream).
**Probe:** `grep -cF 'yield "comments.new:after-save"' isso/ext/notifications.py` (`1`); signal construction anchor: `grep -c 'ext.Signal' isso/__init__.py` (`1`).
**Test:** exercised implicitly by every view test via Stdout logging; no direct unit — coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "Signal subscriptions yield comments.new", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the iterable-subscriber protocol (zero-ceremony plugin surface). Adapt to async dispatch if your handlers do IO. Omit nothing in the event ordering — after-save carries the DB row, finish carries the public projection.
