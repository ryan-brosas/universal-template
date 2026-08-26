<!-- capsule-v2 -->
# Mature logger requirements — what disqualifies console.log, and what shape must log statements take?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c2`; Codebase Memory `nodebestpractices`. **Question:** Which logger capabilities are mandatory for serious projects, and what metadata belongs in each statement?

## Persistent leveled JSON logger (Pino-class); four recommendations; timestamp+multi-destination requirements
**Path/Symbol:** `sections/errorhandling/usematurelogger.md` (:5 console.log verdict + Pino), (:8-11 four recommendations), (:18-26 pino example), (:32-35 StrongLoop requirements), (:39 Winston exclusion pointer #684).
**Signature:** `const logger = pino();` → `logger.info({ anything: 'This is metadata' }, 'Test Log Message with some parameter %s', 'some parameter');`
**Data Shape:** every call = level (debug/info/error) + contextual JSON object + human message; destinations configurable per level.

### Decisive source
```text
# usematurelogger.md :8-11 — the four recommendations verbatim
1. Log frequently using different levels (debug, info, error).
2. When logging, provide contextual information as JSON objects.
3. Monitor and filter logs with a log querying API (built-in to many loggers)
or log viewer software.
4. Expose and curate log statements with operational intelligence tools such
as [Splunk].
# :33-34 — the two hard requirements
1. Timestamp each log line... 2. Logging format should be easily digestible
by humans as well as machines.
```

**Flow:** app logs through ONE centralized persistent logger (pairs with `centralized-handler-not-middleware`) → JSON context makes aggregator properties searchable (`smartlogging` plane) → query/viewer layer filters → ops dashboards curate.
**Invariant:** console.log is disqualified because it's neither persistent nor leveled nor structured — error VISIBILITY is the requirement it fails (:5 title). Context rides as a JSON object argument, not string interpolation, or aggregation can't filter on it. Winston is excluded by deliberate upstream review (#684), not oversight.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'pino' sections/errorhandling/usematurelogger.md` >= 3 && `grep -c 'Timestamp each log line' sections/errorhandling/usematurelogger.md` >= 1 && `grep -c '#684' sections/errorhandling/usematurelogger.md` >= 1.
**Retrieve:** `await mcp.codebase_memory.search_code({ project: "nodebestpractices", pattern: "usematurelogger", limit: 5 });`

## Verdict
Adopt the four recommendations and the timestamp/machine-readable floor as an acceptance checklist for any logger choice. Adapt library (Pino named for performance; any leveled-JSON logger satisfying #684's bar qualifies). Omit vendor dashboard specifics.
