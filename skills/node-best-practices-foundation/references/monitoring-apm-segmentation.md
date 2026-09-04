<!-- capsule-v2 -->
# Ops-plane monitoring & APM segmentation — which metrics are core vs luxury, and what does each tool class actually see?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Which signals must every Node service watch, and why does no single monitoring product cover them all?

## Six core metrics; hardware vs in-process blind spots force tool composition; APM = UX-level tier above
**Path/Symbol:** `sections/production/monitoring.md` (:7 six-metric list + hardware/in-process split + augment recipe), `sections/errorhandling/apmproducts.md` (:6 Exception≠Error premise, :14-20 three APM segments), `sections/production/apmproducts.md` (:7 end-to-end/cross-tier transaction timing, cost caveat), `sections/production/measurememory.md` (:7 leak-prevention guidelines + alerting mandate), (:21-24 v8 ~1.5GB default heap + stop-the-world GC quote).
**Signature:** watch set = CPU, server RAM, Node process RAM (<1.4GB), errors-per-minute, process restarts, average response time. Leak guards: no global-level data, streams for dynamic-size data, let/const scoping.
**Data Shape:** two metric planes — hardware (CPU/RAM: CloudWatch/StackDriver see it) vs in-app (internal error counts, response time: Elastic-class log stacks see it); APM segments = external uptime probes (Pingdom/UptimeRobot) ⊥ code instrumentation agents (NewRelic/AppDynamics) ⊥ operational dashboards (Datadog/Splunk/Zabbix).

### Decisive source
```text
# monitoring.md :7 — the split that forces composition
some metrics are hardware-related (CPU) and others live within the node
process (internal errors) thus all the straightforward tools require some
additional setup... The solution is to augment your choice with missing
metrics, for example, a popular choice is sending application logs to
[Elastic stack] and configure some additional agent (e.g. [Beat]) to share
hardware-related information to get the full picture.
# measurememory.md :22-24 — the heap ceiling
Node.js will try to use about 1.5GBs of memory, which has to be capped when
running on systems with less memory... node –max_old_space_size=400 server.js
```

**Flow:** define the six core metrics first → pick a base tool per plane → AUGMENT with the missing plane's agent → add "luxury" features (DB profiling, cross-service business transactions, BI export, Slack) only after basics work → for user-experience-level questions (slow middleware tier with zero exceptions) escalate to APM, recommended for large-scale products given the price tag.
**Invariant:** Exception ≠ Error — users can be disappointed without any code exception (slow path, downtime). Monitoring without the in-process plane reports healthy hardware while the app drowns; memory leaks specifically REQUIRE proactive external alerting because human watching doesn't scale.
**Probe:** no runner upstream. Deterministic probe: `grep -c '1.4GB' sections/production/monitoring.md` >= 1 && `grep -c 'Exception != Error' sections/errorhandling/apmproducts.md` >= 1 && `grep -c 'max_old_space_size' sections/production/measurememory.md` >= 1.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "APM", limit: 5 });`

## Verdict
Adopt the six-metric floor, the two-plane blind-spot model, and the Exception≠Error escalation trigger. Adapt tool choices to your cloud. Omit vendor names as endorsements; omit the doc-era 1.5GB default (verify against your Node line — pairs with `dual-memory-limits` for the cap mechanics). Per-service complement: `four-signals-service-watchlist` carries this doc's errorhandling-plane twin (Error Rate / Response time / Throughput / Saturation).
