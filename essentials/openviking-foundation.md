# OpenViking — live foundation (source material for the workflow)

> Evidence captured from the live machine, not documentation prose.
> Re-audit before relying: daemon, workspace, and corpus change over time.

## 1. What OpenViking is here

OpenViking is the long-term mined-knowledge store this machine already runs.
It ingests **hermes/pi sessions, skill-mining corpora, and repo-learning passes**
and serves them through `viking://` URIs over MCP at `http://127.0.0.1:1933/mcp`.

## 2. Live evidence (this audit)

| Fact | Value |
|---|---|
| Daemon binary | `~/.hermes/hermes-agent/venv/bin/openviking-server` (running) |
| Server | `http://127.0.0.1:1933` (`auth_mode: dev`, `cors_origins: *`) |
| Storage workspace | `/mnt/hdd/openviking/data` |
| Resource tree | `/mnt/hdd/openviking/data/viking/default/resources/` |
| Vector DB | `vectordb/context` (backend `local`), ~3.9 GB |
| Embedding | provider `voyage`, model `voyage-4-lite`, 2048-dim (key: env-only, never inline) |
| Memory | version `v3`, extraction enabled |
| Retrieval | `hotness_alpha: 0.0`, `score_propagation_alpha: 1.0` |
| Ingest | enabled; harnesses: hermes (`user_field: sender`, mode both) |
| Index queue | `_system/queue` (drained asynchronously) |

## 3. Corpus inventory (exact, at audit time)

- **888 resource dirs** total under `viking://resources/`
  - `llm-repo-learning-*`: **449** (each a repo-learning pass)
  - `*-foundation*` (foundations + pass-N capsule leaves): **284**
  - remainder: probes (`vk_probe`, `lrl-ingest-copy`), specific rows/passes, one-off research
- Every indexed skill in `~/.agents/skills/` has a matching `*-foundation` corpus
  (e.g. `browser-use-foundation`, `ai-sdk-foundation`, `linkedin-scrapers-foundation_9`)
- Read URIs look like `viking://resources/llm-repo-learning-passX-<slug>/…`

## 4. Retrieval surface (exact tool names)

| Tool | Use for | Typical call |
|---|---|---|
| `memgrep` | exact symbols / error strings / regex | `memgrep({pattern, uri, case_insensitive})` |
| `memsearch` | semantic/conceptual questions | `memsearch({query, target_uri?})` |
| `memfind` | fast semantic find (no session context) | `memfind({query, target_uri, limit})` |
| `memread` | read a specific `viking://` URI | `memread({uri, level: aut(o)/abstract###overview})` |
| `memglob` | enumerate files by glob | `memglob({pattern, uri})` |
| `membrowse` | list/tree/stat the store | `membrowse({uri: viking://resources/})` |
| `memadd` | add a file/URL to index (`to` or `parent`) | `memadd({path, to, wait?})` |
| `memqueue` | observer queue status (embedding pending) | `memqueue()` |
| `memcommit` | commit the current Pi session → memories | `memcommit()` |

Guardrails:
- hits are **pointers not proofs** — read the source before citing
- never cite an URIs coverage claim without `memread`-proving it exists
- `memsearch` failing with 5xx ⇒ daemon busy/reindexing; retry `memfind` (fast) instead of assuming missing data
- if the daemon is unreachable, drop to the filesystem store (`/mnt/hdd/openviking/data`) and note the degraded path

## 4. Ingest protocol (source material → essentials)

When new source material arrives (e.g., a Discord export, a doc set, or a chat log):

1. Place material as a Markdown file under `~/work/inbox/` or run one `memadd` with `to: viking://resources/<kebab>/` and `wait: true`.
2. Wait for `memqueue()` to drain (embedding & semantic processing).
3. Point the workflow's context phase at it: `memsearch({query, target_uri: 'viking://resources/<kebab>/'})`.
4. Distill the *exact* quotes into `~/.agents/essentials/` (verbatim blocks with source URI), because essentials are the durable, host-neutral reference every CLI reads.
5. The counts/provenance table above is updated each time material is absorbed — do not drift.

## 5. Discord message material — FOUND (audited 2026-08-26)

The exact Discord message material **is** in OpenViking and is now source material for the workflow:

- **Verbatim threads** (byte-exact, deduped by content hash): `essentials/discord-material/raw/`
  — scanning all **2849 session archives** (session
  `20260822_231822_f198ed/history/archive_001/messages.jsonl`) surfaced **5 unique Discord
  threads**: 2026-08-21 (Tom: code is ground truth, no specs, prewalk=best tool), 2026-08-11
  (AGENTS.md over-restriction → steer outcomes not behavior), 2026-07-26 (stacking leverage,
  capture-into-skills ritual), 2026-07-19 (mechanical tests & quality packs), 2026-08-03
  (catch-first test & gate methodology).
- **Distilled OpenViking patterns** (byte-identical): `essentials/discord-material/patterns/`
- **Thread → pillar mapping:** `essentials/discord-material/README.md`.

`~/.hermes/hermes-agent/plugins/platforms/discord/` is adapter *code*, not message content —
irrelevant here.

**When future Discord exports arrive** (DiscordChat JSON, a raw chat log, a hermes
channel thread), run the ingest protocol in §4 first, then add the messages **verbatim**
under `essentials/discord-material/raw/` with their source URI — that is how the material
stays live as the workflow develops from it.