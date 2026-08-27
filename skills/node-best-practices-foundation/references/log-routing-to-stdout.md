<!-- capsule-v2 -->
# Log routing to stdout — who owns log DESTINATION, and what code shape keeps that decision out of the app?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** Where do log destinations (file, DB, Splunk) belong — in application code or in the execution environment — and what breaks when they live in the app?

## App writes unbuffered to stdout/stderr; the execution environment routes
**Path/Symbol:** `sections/production/logrouting.md` (title :1, explainer :7, separation-of-concerns :9, winston anti-pattern :18-21, daemon.json example :52-58, pipeline :63, 12-factor quote :74-77).
**Signature:** app code → logger → `stdout`/`stderr` only; container `daemon.json` `"log-driver"` (e.g. splunk) picks up the stream; full pipeline `log -> stdout -> Docker container -> Splunk` (:63).
**Data Shape:** two owners — APP owns WHAT to log (level, JSON context, transaction id — see `mature-logger-contract`, `transaction-id-correlation`); EXECUTION ENVIRONMENT owns WHERE it goes (file/DB/SaaS sink). The anti-pattern shape (:18-21): winston `transports.File({ filename: 'combined.log' })` + `winston.transports.MongoDB` inside app code — "the application now handles both application/business logic AND log routing logic".

### Decisive source
```text
// logrouting.md :7 — the split
Application code should not handle log routing, but instead should use a
logger utility to write to `stdout/stderr`.
// :9 — why destinations must stay out of code
What happens if you define the log locations in your application, but later
you need to change that location? That results in a code change and deployment.
... The execution environment (container) should decide where the log files
get routed to instead.
// :77 — the 12-factor floor
A twelve-factor app never concerns itself with routing or storage of its
output stream. It should not attempt to write to or manage logfiles. Instead,
each running process writes its event stream, unbuffered, to stdout.
```

**Flow:** app logs through its leveled JSON logger to stdout/stderr (no file/DB transports) → container runtime captures the stream per `daemon.json` log-driver config → DevOps changes sinks by editing environment config, never app code → scaling/relocation never strands a logfile on a dead instance (:9: "we can't be sure where a logfile will end up").
**Invariant:** changing a log destination must NOT require a code change and deployment; destination knowledge lives in exactly one place (the execution environment), owned by the people who operate it (often DevOps, not app developers, :9). File/DB transports inside app code couple business logic to infrastructure and break on scale-out.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'daemon.json' sections/production/logrouting.md` = 1 && `grep -c 'unbuffered' sections/production/logrouting.md` = 1 && `grep -c 'winston-mongodb' sections/production/logrouting.md` = 2.
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live 2026-08-26:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "daemon.json", "limit": 8}'
# resolves `sections/production/logrouting.md` Module 1-88 line-exact (English top hit among 7 translation twins; verified 2026-08-26)
```

## Verdict
Adopt the stdout-only app contract for any containerized service; move every file/DB transport out of app code into the platform's log-driver config. Adapt the sink mechanism (daemon.json vs K8s log collection vs cloud agent) per platform. Omit nothing behavioral — destination-in-code is the trap this doc exists to name. Pairs with `mature-logger-contract` (WHAT to log) and `transaction-id-correlation` (id rides each line).
