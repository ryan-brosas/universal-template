<!-- capsule-v2 -->
# Bootstep blueprint — how does a worker assemble ordered startable components from a flat list?

**Source:** Celery BSD-3-Clause `main@8d2bccca0478cad48f31a75eaebc0ce389f65425`; Codebase Memory `ext-celery`. **Question:** How do components declare dependencies, get topologically sorted, and shut down in reverse without one bad step killing the worker?

## Blueprint / Step / StartStopStep
**Path/Symbol:** `celery/bootsteps.py:Blueprint` (:74-263), metaclass `StepType` :266, `Step` :288, `StartStopStep` :355, `ConsumerStep` :386; worker wiring `celery/worker/worker.py:WorkController.Blueprint.default_steps` (:76-84).
**Signature:** `Blueprint.apply(parent, **kwargs)` → sets `.order` (toposorted step instances) and calls each `step.include(parent)`; `Blueprint.start(parent)` iterates `step.start(parent)`; `send_all(parent, method, ..., reverse=True, propagate=True)` — callers pass `propagate=False` for stop/terminate via `restart()`.
**Data Shape:** Steps are CLASSES with `name` (defaults to qualname via metaclass), `requires` (tuple of import strings or classes), `last=False`, `conditional=False`, `include_if(parent)` predicate; `StartStopStep.include` stores created service on `self.obj` and appends to `parent.steps`.

### Decisive source
```python
# celery/bootsteps.py:186-211 — graph build and topsort
def apply(self, parent, **kwargs):
    order = self.order = []
    steps = self.steps = self.claim_steps()      # name→class by qualname
    for S in self._finalize_steps(steps):
        step = S(parent, **kwargs)               # __init__ may mutate parent
        steps[step.name] = step
        order.append(step)
    for step in order:
        step.include(parent)
    return self

def _finalize_steps(self, steps):
    last = self._find_last()
    self._firstpass(steps)          # pull transitive requires into blueprint
    G = self.graph = DependencyGraph(
        ((C, C.requires) for C in steps.values()),
        formatter=self.GraphFormatter(root=last))
    if last:
        for obj in G:
            if obj != last:
                G.add_edge(last, obj)   # Consumer starts after everything
    try:
        return G.topsort()
    except KeyError as exc:
        raise KeyError('unknown bootstep: %s' % exc) from exc
```
```python
# celery/bootsteps.py:137-153 — send_all; stop/terminate pass propagate=False via restart() :132-134
def send_all(self, parent, method,
             description=None, reverse=True, propagate=True, args=()):
    steps = reversed(parent.steps) if reverse else parent.steps
    for step in steps:
        fun = getattr(step, method, None)
        if fun is not None:
            try:
                fun(parent, *args)
            except Exception as exc:
                if propagate:
                    raise
                logger.exception('Error on %s %s: %r', ...)
```

**Flow:** claim declared+default step classes by string qualname → firstpass resolves `requires` transitively so deps outside the declared set join the same blueprint → DependencyGraph topsort orders; the single `last=True` step (Consumer in worker blueprint; Evloop inside consumer blueprint) gets an edge to every node guaranteeing it starts LAST → include phase instantiates services (`create`) with `include_if` gating → start runs forward calling `obj.start()` → stop/terminate run through `restart()` in REVERSE with `propagate=False`, errors logged-not-raised — BUT `close()` runs FORWARD (`send_all(..., 'close', reverse=False)`, :130): close order is start-order, only stop/terminate are reversed → `stop()` short-circuits unless fully started (`state != RUN or started != len(parent.steps)` → jump straight to TERMINATE).
**Invariant:** (1) Exactly ONE `last=True` step per blueprint. (2) Step `__init__` runs during apply and is allowed to mutate the parent (e.g. Heart sets `c.heart=None`) — ordering of side effects matters as much as start order. (3) Startup exceptions PROPAGATE (blueprint.start has no try/except); only shutdown is forgiving. (4) Unknown dependency surfaces as `KeyError('unknown bootstep: ...')`.
**Probe:** `t/unit/worker/test_bootsteps.py::test_blueprint_name` (:62), `test_create`/:76; consumer-side restart semantics pinned by `t/unit/worker/test_consumer.py::test_max_restarts_exceeded` (:373).
**Retrieve:**
```json
{"project":"ext-celery","query":"Blueprint topsort StartStopStep requires","limit":5,"detail":"ids"}
```
## Verdict
Adopt: declare-deps-as-strings + transitive claim + topsort + single-last-step + reverse-forgiving-shutdown (stop/terminate only; close runs forward — see Flow). Adapt symbol_by_name string loading to your DI style. Omit the GraphFormatter/dot visualization and `connect_with` blueprint stitching unless you need runtime graphs. Needle-verifier battery 2026-08-24 @ unchanged pin 8d2bccca: all Path/Symbol spans, quoted source, probes, and Retrieve live-re-executed GREEN post-repair (spans had drifted ~18-56 lines from the pass-1 authoring read; send_all default-propagate + close-forward semantics corrected against source).
