<!-- capsule-v2 -->
# Four user-facing service signals — which four signals must EVERY service watch, and what does each one explain?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d54`; Codebase Memory `nodebestpractices`. **Question:** Above raw metrics, which per-service signals reveal user-facing failure, and what is each signal FOR?

## Error Rate / Response time / Throughput / Saturation — the all-services watchlist
**Path/Symbol:** `sections/errorhandling/monitoring.md` (:1-2 title — monitoring defined in the ERROR-HANDLING plane; :3-4 alerting-first explainer header; :5 core-metric floor incl. Node process RAM <1.4GB and email/Slack notification bar; :7 hardware-vs-in-process blind spots + Elastic+Beat augmentation recipe; :9-16 four-signal watchlist blog quote). Production twin: `sections/production/monitoring.md` via `monitoring-apm-segmentation` (six-metric ops floor).
**Signature:** watch(service) → {Error Rate, Response time, Throughput, Saturation}; each signal carries an explicit because-clause tying it to customer/business impact.
**Data Shape:** service-level signal → interpretation: Error Rate = user-facing failures NOW; Response time = latency's direct business cost; Throughput = CONTEXT that explains error/latency spikes; Saturation = headroom ('if CPU is 90%, can your system handle more traffic?').

### Decisive source
```text
# monitoring.md :13-16 — the watchlist, verbatim
We recommend you to watch these signals for all of your services:
Error Rate: Because errors are user facing and immediately affect your customers.
Response time: Because the latency directly affects your customers and business.
Throughput: The traffic helps you to understand the context of increased error rates and the latency too.
Saturation: It tells how "full" your service is. If the CPU usage is 90%, can your system handle more traffic?
# monitoring.md :5 — the alerting-first definition of monitoring itself
monitoring means you can easily identify when bad things happen at production. For example, by
getting notified by email or Slack.
```

**Flow:** define the small core metric floor first (:5) → wire notifications so failures ANNOUNCE themselves (email/Slack) → for every service keep the four-signal dashboard live → read spikes THROUGH throughput: rising errors/latency during a traffic surge tells a different story than at idle → act on saturation before errors start (headroom is the leading indicator).
**Invariant:** the four signals are SERVICE-level and customer-facing — they complement, never replace, the ops-plane six-metric floor (CPU/server-RAM/process-RAM/errors-min/restarts/response-time) and its two-plane tooling split; a monitoring stack that cannot answer 'how full is the service?' is incomplete even with green hardware graphs.
**Probe:** no upstream runner exists (docs-only repo). Deterministic probe, executed green at pin: `grep -c 'Error Rate' sections/errorhandling/monitoring.md` = 1 && `grep -icE 'saturation' sections/errorhandling/monitoring.md` = 1 && `grep -c 'Response time' sections/errorhandling/monitoring.md` = 1 && `grep -c 'Throughput' sections/errorhandling/monitoring.md` = 1 && `grep -c '1.4GB' sections/errorhandling/monitoring.md` = 1.

## Get live surrounding code
**Retrieve:** doc-shaped-graph note — BM25 `search_graph` returns ZERO tokens here; `search_code` with the decisive needle resolves the pinned file uniquely. Executed live:
```ts
await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "Saturation", limit: 5 });
// => top English hit: nodebestpractices.sections.errorhandling.monitoring Module sections/errorhandling/monitoring.md 1-18, matches "16"
```

## Verdict
Adopt the four-signal floor as a per-service SLO checklist and the because-clauses as each signal's alert rationale; pair with `monitoring-apm-segmentation` for which TOOL class can even see each plane. Adapt thresholds (the 90%-CPU example is illustrative) and notification channels to your stack. Omit doc-era figures as facts (the <1.4GB process-RAM ceiling pairs with `dual-memory-limits` and must be re-derived for your Node line); omit vendor names as endorsements.
