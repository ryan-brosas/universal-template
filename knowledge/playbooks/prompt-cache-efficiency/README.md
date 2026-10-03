---
title: prompt-cache-efficiency
summary: "Use when prompt-cache hit rate is low or a target is set (for example 98% cached input): quantify the write and uncached-input miss budget, remove mid-session prefix churn, and verify per session."
kind: playbook
---

# Prompt cache efficiency

The reported rate is `cache_read / (cache_read + cache_write + uncached_input)`.
Reads grow with use; writes and uncached input are the miss budget. Raise the
rate by shrinking misses, not by chasing more reads.

`check-cache.sh` in this directory prints the overall and per-model rates plus
the 98/99% miss budgets; pass `--days N` for a rolling window. It is safe to
rerun.

## Targets

Use a rolling window, not lifetime: history already contains misses that future
reads can only dilute, and lifetime 98% would need roughly 56M of additional
clean reads. The working targets are a rolling 7-day rate of at least 98%
(stretch 99%), per-session rates at or above 99% for long sessions, and
cache-blind volume reported separately.

Measured attribution from the largest recorded session (128 steps, 24.4M cache
reads): 101 natural turns averaged 520 write against 211k read per step
(99.75% per-step efficiency), while four full-context invalidations above 100k
wrote 84% of that session's 1.06M writes. One invalidation costs about a full
context; a frozen session has almost no natural write overhead.

## Size the budget

For a target rate, the allowed miss budget is `reads × 0.02 / 0.98` at 98% and
`reads / 99` at 99%. Compare it with the current `cache_write + input`. Misses
cluster by cause:

- Large cache writes after a mid-session prefix change: editing instructions,
  AGENTS.md, skills, agents, configuration, or MCP servers, or switching model.
- Uncached input on cache-blind routes: usage payloads without cached-token
  details count every prompt as input even when the upstream caches.
- One-shot child sessions: each writes its prefix and reads it once.

A single mid-session config edit can add a write of roughly a whole prefix,
more than a session's first turn costs. Treat instruction and config edits as
session-boundary work.

## Keep the prefix stable

- Batch instruction, AGENTS.md, skill, agent, and MCP changes at session
  boundaries; each change invalidates everything after it.
- Keep one model and provider per session; exercise new routes in separate
  sessions.
- Attach context early; late insertions invalidate the tail of the prefix.
- Do not connect or disconnect MCP servers mid-session; tool schemas sit in the
  cached prefix.

## Shape sessions for reuse

- Continue an existing session for related work instead of starting a new one,
  and keep turns inside the provider's cache lifetime.
- Give a subagent a batch of work; a one-shot child always pays a write it
  never reads back.
- Keep sessions focused so compaction, which invalidates once, happens less.

## Route by cache behavior

Keep high-volume work on providers that report cache reads and writes; a
cache-blind route's tokens count as uncached input regardless of upstream
caching. Use cache-blind routes for short, visual, or lookup work — route by
value, not by the metric.

## Verify

Track per-session rates (`opencode2 stats --cost --project .`); lifetime
averages move slowly. A long session with a frozen prefix should hold at or
above the target, and a mid-session config edit shows up as a write spike at
the next check.

To learn a provider's cache lifetime, leave a session idle for 30 and 60
minutes, send one turn, and compare the write delta; fold the result into how
long a session stays warm.
