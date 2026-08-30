# mcp-context — the context source inventory

The retrieval layer backing workflow-lifecycle. Routing is need-driven: pick
one primary source per question, escalate only after a named gap, and stop
when evidence is sufficient (`skills/evidence-router/SKILL.md` is the
canonical routing policy). The inventory below exists so you know what each
registered source is good for — it is not an ordered ritual to walk on every
task.

## Plumbing rule

- Tool names differ per host CLI. This capsule lists the refs as they appear in
  Pi (MCP namespace `mcp.*` or Pi extensions `extensions.*`). On Claude Code,
  Codex, or DSH the same servers surface under their own tool names — the
  contract is "server name + capability", not the exact ref.
- Any source that is not registered at runtime is skipped with a note; never
  fake a server, and never cite a hit you did not verify.
- Retrieval hits are pointers, not proofs — read the actual source before
  implementing or making load-bearing claims.

## Codebase Memory (active project graph)

Server: `codebase-memory-mcp` (stdio). Probe-first rule: `index_status` →
`search_graph`/`query_graph` → `trace_path` → `get_code_snippet`.

| Step | Tool (Pi ref) | Use |
|---|---|---|
| Coverage probe | `codebase_memory.index_status` | node/edge counts + coverage report (parse_partial/skipped/not_indexed) |
| Structural query | `codebase_memory.search_graph` / `query_graph` | filtered graph queries, `graph=missed` for index misses |
| Trace | `codebase_memory.trace_path` | callers/callees, blast radius |
| Source | `codebase_memory.get_code_snippet` | rendered, file-anchored code |
| Maintenance | `codebase_memory.index_repository` / `manage_adr` | only when the user asked to index or record an ADR |

Guardrail: if the status report flags a file as parse_partial/skipped, grep that
file locally and do not trust graph completeness for it. The graph is a
navigation index, never source of truth.

## OpenViking (mined corpora)

Local daemon: `~/.hermes/hermes-agent/venv/bin/openviking-server`, serving
streamable-http `http://127.0.0.1:1933/mcp`. Storage workspace has evidence
in `/mnt/hdd/openviking/data` (resources tree at
`/mnt/hdd/openviking/data/viking/default/resources/`; vectordb `context`,
voyage-4-lite 2048-dim, ~3.9 GB; memory v3, extraction on;
`hotness_alpha 0.0` / `score_propagation_alpha 1.0`). In Pi it is exposed as
extensions (`extensions.*`); in DSH hosts it is the `openviking` server.
This is the layer that reuses prior mining and durable experience
(`llm-repo-learning-*`, `*-foundation`, `viking://resources/<name>`,
session memories): past decisions, failed attempts, lessons, and recurring
edge cases. Enumerate the live corpus with `membrowse` at runtime instead of
trusting hard-coded counts.

Live facts and the **ingest protocol** for new source material (Discord
exports, doc sets, chat logs) live in
[`~/.agents/essentials/openviking-foundation.md`](/home/utopia/.agents/essentials/openviking-foundation.md):
place the material under `viking://resources/<kebab>/` (or `~/work/inbox/`),
`memqueue()` until drained, then distill *verbatim* quotes into essentials.
The Discord-message material section there is dated and evidence-backed:
**the exact threads were found in OpenViking** (session
`20260822_231822_f198ed/history/archive_001/messages.jsonl`) and harvested
byte-verbatim into
[`~/.agents/essentials/discord-material/`](/home/utopia/.agents/essentials/discord-material/)
(`raw/` = 5 deduped threads; `patterns/` = distills;
`README.md` maps each thread to its pillar doc). When this workflow cites
the Discord material, quote the verbatim block from `discord-material/`, not
paraphrase.

| Step | Tool (Pi ref) | Use |
|---|---|---|
| Semantic | `extensions.memsearch` | concepts/ideas ("how does X do Y") |
| Fast find | `extensions.memfind` | quick relevance scan with `target_uri` narrowing |
| Exact | `extensions.memgrep` | symbols, error strings, class/function names |
| Browse | `extensions.membrowse` | directory tree, `stat` a URI before reading |
| Globs | `extensions.memglob` | enumerate candidate files by `**/...` |
| Read | `extensions.memread` | read a `viking://` URI and show evidence |
| Add | `extensions.memadd` | register a remote URL / local file under `viking://resources/` |
| Commit | `extensions.memcommit` | persist session decisions/memories at the end of a lesson |

Use `memgrep` before `memsearch` when you know the exact symbol; `memsearch`
for conceptual questions; always `memread` a hit before citing it.

## Context7 (library docs + code examples)

Server: `context7` (stdio `npx -y @upstash/context7-mcp`, key in
`CONTEXT7_API_KEY` env).

- `context7.resolve-library-id` — map a package/product name to `/org/project[/version]`.
- `context7.query-docs` — one concept per call; at most 3 calls per question.

Use when a question actually needs up-to-date library documentation, API
usage, versions, or code examples for a dependency. Version pin `@version`
only for concrete version questions.

## Exa (web + live sources)

Server: `exa` (stdio `npx -y exa-mcp-server`, env `EXA_API_KEY`). Tools are
the exa-mcp-server set (`exa_search` / search+contents variants; probe the
server with `mcp({server / describe})` for the exact names).

Use for verifying that a claim is live (current versions, releases, breaking
changes), finding upstream sources, or gap-filling when the local graph,
corpora, and docs have nothing. Treat web hits as pointers — read the linked
source before assertion.

## DeepWiki (OSS architecture pages)

Server: `deepwiki` (stdio `npx -y deepwiki-mcp`).

| Tool | Use |
|---|---|
| `deepwiki.get-deepwiki-index` | get the page list for owner/repo |
| `deepwiki.get-deepwiki-page` | read a page (components, flows) |

Use for big open-source internals during learn/audit when you need the
architecture narrative beside the code in the graph or corpus.

## Per-command recipe

| Command | Primary sources | Why |
|---|---|---|
| init | active graph → corpora → dependency docs → live check of pinned versions | graph grounds structure; corpora apply prior solutions; docs/live only for detected deps |
| learn | corpora (did we mine this?) → source verify → DeepWiki narrative | corpus first, source cross-check, cite SKILL.md |
| audit | graph + corpora → DeepWiki → Exa | trace the pattern, then confirm current best practice |
| verify | none | run the real commands + gates; probes only when a claim cites graph/corpus |
| gc | none | filesystem + repo state only |

## Guardrails

- Retrieval hits are pointers, not proofs — read the source or run the command.
- Never cite unindexed/flagged code without a local grep.
- Secrets: env only; do not hardcode keys in the `servers.json` — use `${VAR}` placeholders (exported by the host shell).
- MCP absent for a source → filesystem fallback + note it in the evidence record.
- No MCP registered at all: run the workflow on filesystem facts alone and say so; never fabricate a "probable" hit.
