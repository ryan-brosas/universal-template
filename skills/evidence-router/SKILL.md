---
name: evidence-router
description: "Use when choosing a bounded retrieval route for local code, inspiration repositories, GitHub overviews, library docs, or current web facts."
disable-model-invocation: true
---

# Evidence Router

Pick one primary route per question, escalate only on a named gap, and stop
once evidence is sufficient. Keep tool names discoverable and current rather
than guessing a provider action.

## Core Principle

Pick one primary route per question, escalate only on a named gap, and stop once evidence is sufficient.

## When to Use / NOT

**Use** — choosing a bounded retrieval route for local code, inspiration repositories, GitHub overviews, library docs, or current web facts.

**NOT** — when one primary source already answers the question (stop, don't route further); when the ask is unbounded exploration (each source is capped as shown in the table).

## Workflow

1. Choose the primary route from the Routes table for the need.
2. Escalate one step in the Escalation Order only after a named gap.
3. Record each finding in the Evidence Record.
4. Stop when one primary source answers or two independent sources agree; otherwise report the open evidence gap.

## Routes

| Need                                          | Tool                                                                                               | Budget                          |
|-----------------------------------------------|----------------------------------------------------------------------------------------------------|---------------------------------|
| Active-project architecture and relationships | `codebase-memory_get_architecture` → `codebase-memory_search_graph` / `codebase-memory_trace_path` | bounded by query and pagination |
| Local code search, callers, callees, complexity | `codegraphcontext_find_code` → `codegraphcontext_analyze_code_relationships`                      | one query, bounded depth        |
| Exact IDE symbol or call hierarchy            | `ide_idea_skill_search` / `ide_idea_search_symbol` → `ide_idea_analyze_calls`                      | one symbol and bounded depth    |
| Literal/config search and exact source        | JetBrains text/regex search → `ide_idea_read_file`                                                 | selected paths and ranges       |
| Blast radius / architectural impact           | `codegraphcontext_simulate_architectural_change` → `codegraphcontext_simulate_metrics`              | one repo, one change set        |
| Inspiration repositories                      | `codebase-memory_list_projects` → one project's graph/architecture tools                           | one repository per question     |
| GitHub repository overview                    | `mcp.deepwiki.get-deepwiki-index` → `mcp.deepwiki.get-deepwiki-page`                               | one index + one page            |
| Library or API docs                           | `mcp.context7.resolve-library-id` → `mcp.context7.query-docs`                                      | max three topics                |
| Current facts and discovery                   | `extensions.openai_websearch`                                                                      | 3–5 cited results               |
| Selected page content                         | a discovered read-only fetch/crawl capability                                                      | selected URLs only              |

## Escalation Order

1. Codebase Memory for architecture, definitions, relationships, traces, and
   inspiration-repository comparison. Check coverage for cited paths and scopes.
2. CodeGraph Context (`codegraphcontext`) for local active-project code search,
   caller/callee tracing, dead-code, complexity, and blast-radius simulation when
   Codebase Memory is unavailable or lacks FalkorDB-indexed local coverage.
3. JetBrains IDE tools for exact symbols, call hierarchy, literal/config search,
   dependency source, and source confirmation before edits.
4. Pi Fovea when graph and IDE coverage is unavailable.
5. DeepWiki index/page for a bounded GitHub overview.
6. Context7 for current versioned library documentation; resolve the library ID
   first unless the user supplied `/org/project[/version]`.
7. Codex web search for current facts or discovery when the earlier routes do
   not answer the question.
8. A discovered read-only fetch/crawl tool for one already-selected URL.

Move one step only after a named gap: Codebase Memory is unavailable, stale,
partial, or truncated; the codegraph index is absent or stale; the IDE cannot
resolve the symbol; Fovea lacks the node; DeepWiki has no relevant page;
Context7 lacks the version; or the cited shortlist lacks a primary source.

## Optional Veda synthesis

Use Veda's AGY Gemini profiles as a bounded, economical second read after the primary evidence route:

1. `repo-scout` with `gemini-lite` maps files, symbols, and gaps.
2. `context-curator` with `gemini-mid` compresses selected findings into a handoff packet.
3. `frontend-auditor` with `gemini-ui` checks UI states, responsive behavior, accessibility, and visual risks.
4. `cross-system-synthesizer` with `gemini-pro-low` resolves contradictions before a load-bearing plan.

Then invoke direct AGY Claude Opus for architecture planning or high-risk review. Veda Gemini passes are advisory, not evidence; preserve primary tool calls, source citations, and the evidence ledger. Do not invoke `veda -b agy -m claude-*`: the adapter injects `--effort`, which the AGY Claude models reject. If a lane is unavailable, continue with Pi-native evidence and report the gap.

## Evidence Validity

A GitHub repository is a lead, not automatically authoritative evidence. Capture
owner/repo, commit or branch, retrieval date, and license; verify important
claims against code, tests, and official documentation. A Codebase Memory graph
is an indexed navigation snapshot, not a truth store; confirm exact source and
inspect coverage metadata before negative or exhaustive claims.

## Anti-Splurge Rules

- Deduplicate findings by question plus source.
- Summarize before expanding a source.
- Parallelize only independent angles.
- Cap each source as shown in the table.
- Stop when one primary source answers the question or two independent sources
  agree; otherwise report the open evidence gap.

## Evidence Record

For each finding record the claim, source tool, exact call, URL or context, date,
and confidence. Unknowns stay `[NEEDS CLARIFICATION: reason]`; no source, no
claim.

## Red Flags

Guessing a provider action instead of keeping tool names discoverable and current; duplicate retrieval of the same question plus source; unbounded expansion of a source; a GitHub repository treated as authoritative evidence without owner/repo, commit or branch, retrieval date, and license capture; a Codebase Memory graph treated as a truth store for negative or exhaustive claims; a claim with no source.

## Verification

Verify important claims against code, tests, and official documentation. Confirm exact source and inspect coverage metadata before negative or exhaustive claims. Each finding records the claim, source tool, exact call, URL or context, date, and confidence; unknowns stay `[NEEDS CLARIFICATION: reason]`.

## Skill Result Contract

<skill_result>
  <skill>evidence-router</skill>
  <status>success|partial|blocked|failure</status>
  <evidence>One primary route, named gaps, bounded calls, compact evidence records</evidence>
  <artifacts>Routed evidence ledger</artifacts>
  <risks>Duplicate retrieval, unbounded expansion, unavailable capability, or none</risks>
</skill_result>

## References

N/A — no reference files; routes, escalation order, and validity rules are inline in this skill.
