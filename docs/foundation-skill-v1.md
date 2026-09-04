# Foundation skill v1 migration evidence

Evidence captured 2026-09-04 on `refactor/foundation-skills`. This is a
migration/probe record, not a timeless host compatibility promise. Re-probe
installed host versions before changing setup guidance.

## Corpus result

All 194 `*-foundation` directories moved from the retired top-level foundation
root into the single `skills/` tree. Each is a real directory (not a symlink),
has `kind: foundation`, `invocation: manual`, and
`disable-model-invocation: true`, and points to `references/index.md`. The
index preserves the former loader's detailed inventory, provenance, boundaries,
and every reference-file link. Foundation loaders state that current project
source/tests/runtime outrank the historical projection and require selecting
one matching capsule rather than bulk-loading.

| Loader measure | Before | After |
| --- | ---: | ---: |
| Files measured | 194 | 194 |
| Words | 487,769 | 45,181 |
| Bytes | 4,570,849 | 387,351 |
| Lines | 20,293 | 7,545 |
| Words, min / median / max | 519 / 1,342 / 21,625 | 192 / 224 / 315 |
| Bytes, min / median / max | 4,968 / 12,461 / 200,114 | 1,627 / 1,919 / 2,895 |
| Lines, min / median / max | 40 / 75 / 649 | 38 / 39 / 44 |

Loader words fell 90.7%. Evidence was moved, not discarded: the detailed
content now lives in each foundation's `references/index.md` next to its
capsules.

## Startup metadata budget

The tracked operational catalog was and remains **153 skills: 38 visible, 115
hidden**, with **10,315 visible characters (~2,578 tokens)**. Foundations are
excluded from those operational/startup counts. Their 194 name+description
records total 89,630 characters (~22,407 tokens); an eager host pointed at the
unfiltered tree can expose that avoidable metadata, so eager or unverified
hosts must use the filtered hot discovery route in `README.md`. The current
versioned payload and MCP measurements are in `context-surfaces.md` and
`context-measurements.json`; this section remains migration evidence.

## Installed-host probes

All commands used temporary HOME/config roots where the host supported them.
No host configuration in the real home was changed. No successful model turn
was used as evidence.

| Host/version | Probe and observed result | Disposition / limitation |
| --- | --- | --- |
| Pi 0.84.4 | Installed `docs/skills.md` and `dist/core/skills.js` were read. Pi recursively scans configured skill roots, parses `disable-model-invocation`, and filters hidden skills in `formatSkillsForPrompt`. | Hidden foundations do not enter Pi's model prompt, but the host is still an eager scanner. Use `--no-skills --skill <filtered-view>`; pass one foundation explicitly only for a selected capsule task. |
| Claude Code 2.1.247 | A temporary `~/.claude/skills` with one operational fixture and one hidden-foundation fixture produced debug evidence: “Loaded 2 unique skills”; startup stopped on an invalid model before a model turn. A filtered-view rerun loaded exactly one skill. | The local probe proved eager discovery and the filtered route, not whether attachment/model invocation honors the hidden field. Treat exposure as unverified and install only the filtered view. |
| Codex CLI 0.151.0 | Temporary `CODEX_HOME` `codex doctor --json --summary` loaded config and reported `skill_search` enabled, but exposed no skill inventory; no credentials were present. A prior doctor reachability check timed out. | Hidden-field and startup behavior were not testable without a model session. Treat as unverified; expose only filtered operational links under the host's skill root. |
| Gemini CLI 0.58.0 | `gemini skills link` against a two-fixture directory, followed by `gemini skills list --all`, listed both `probe-visible` and `probe-hidden-foundation` as enabled. Linking a one-symlink filtered view listed the operational fixture and not the foundation. | The host did not filter `disable-model-invocation` in discovery. Link a filtered operational view, never the unified root. |
| OpenCode 1.18.27 | In a temporary project, `opencode debug skill --pure` returned both fixtures, including the hidden foundation. With `OPENCODE_DISABLE_EXTERNAL_SKILLS=1` and `skills.paths` set to a one-symlink filtered view, only the operational fixture remained. Its built-in customization skill documents recursive `**/SKILL.md` scans. | The host ignored the hidden field in discovery. Disable external scans and configure `skills.paths` to a filtered operational view. |
| Cursor Agent 2026.08.11-e8db854 | Temporary workspace startup with an invalid model stopped at local model validation. Help exposes no skill inventory command. | Discovery/hidden behavior was not observable without a real model turn. Treat as unverified; point any `.agents/skills.json` integration at a filtered view. |
| AGY 1.1.26 | Temporary `--add-dir` startup with an invalid model stopped at local model validation. Help documents skill expansion but no inventory command; installed binary strings identify workspace `.agents/skills/<name>/SKILL.md`. | Hidden behavior was not observable without a real model turn. Treat as unverified; expose only filtered operational links. |

“Listed” or “loaded” is not claimed as model-visible unless the probe showed
that boundary. Gemini and OpenCode demonstrated unfiltered discovery; Pi's
installed implementation demonstrated prompt filtering; the other four remain
explicitly unverified.

## Filtered discovery route

Keep `skills/` canonical. For eager or unverified hosts, create a host-owned
**symlink view** containing only tracked hot skill directories (operational
entries not hidden by `disable-model-invocation`) and configure that host to
scan the view. Do not copy files and do not create a second canonical tree.
Maintainers can obtain the exact source set with:

```sh
python3 scripts/skill-catalog.py list --surface hot --json
```

A foundation remains available through explicit
`skill-catalog.py search/show`, then direct loading of its `SKILL.md`, index,
and one selected capsule. Rebuild/reconcile the symlink view after catalog
changes, preserving unrelated host files. The temporary filtered-view probe was
observed on Claude, Gemini, and OpenCode; other hosts retain the limitations in
the table above.

## Per-loader measurements

These are byte/word counts over each `SKILL.md`; they establish that every
loader was measured rather than inferred from a sample. Per-loader line counts
were also measured and feed the aggregate table above.

| Foundation | Before words | After words | Before bytes | After bytes |
| --- | ---: | ---: | ---: | ---: |
| `aeo-affiliate-skills-foundation` | 621 | 229 | 5,219 | 2,043 |
| `aeo-elmo-foundation` | 929 | 201 | 8,670 | 1,753 |
| `affine-foundation` | 1,403 | 224 | 13,483 | 1,889 |
| `agency-swarm-foundation` | 855 | 219 | 7,734 | 1,914 |
| `agent-s-foundation` | 692 | 205 | 6,703 | 1,782 |
| `agentic-seo-skill-foundation` | 1,254 | 245 | 12,112 | 2,180 |
| `agno-foundation` | 1,375 | 254 | 12,242 | 2,106 |
| `ai-foundation` | 21,625 | 214 | 200,114 | 1,817 |
| `aider-foundation` | 2,635 | 218 | 24,822 | 1,845 |
| `airflow-foundation` | 856 | 199 | 8,040 | 1,685 |
| `aliasvault-foundation` | 1,237 | 208 | 11,353 | 1,722 |
| `analytics-foundation` | 929 | 219 | 8,581 | 1,904 |
| `appflowy-foundation` | 743 | 222 | 6,813 | 1,835 |
| `autogen-foundation` | 1,914 | 253 | 17,493 | 2,244 |
| `awaithumans-foundation` | 2,634 | 223 | 27,857 | 1,836 |
| `baserow-foundation` | 887 | 202 | 8,175 | 1,698 |
| `billion-context-pi-foundation` | 1,922 | 200 | 17,903 | 1,752 |
| `biome-foundation` | 8,218 | 218 | 86,829 | 1,839 |
| `browser-harness-foundation` | 1,547 | 214 | 15,487 | 1,766 |
| `browser-harness-js-foundation` | 4,584 | 207 | 41,169 | 1,792 |
| `browser-use-foundation` | 3,566 | 210 | 35,257 | 1,740 |
| `bruno-foundation` | 1,359 | 206 | 12,660 | 1,732 |
| `camel-foundation` | 914 | 194 | 8,446 | 1,679 |
| `cap-foundation` | 931 | 204 | 9,008 | 1,918 |
| `celery-foundation` | 1,692 | 241 | 15,474 | 1,984 |
| `changedetection-foundation` | 723 | 221 | 6,291 | 1,933 |
| `chatwoot-foundation` | 909 | 238 | 7,891 | 2,044 |
| `chroma-foundation` | 1,250 | 220 | 10,828 | 1,867 |
| `cline-foundation` | 4,194 | 312 | 38,429 | 2,895 |
| `codebase-memory-mcp-foundation` | 2,509 | 221 | 28,600 | 1,939 |
| `codedb-foundation` | 899 | 244 | 7,497 | 1,994 |
| `cognee-foundation` | 1,218 | 230 | 11,972 | 1,950 |
| `continue-foundation` | 2,450 | 270 | 24,946 | 2,263 |
| `coolify-foundation` | 1,120 | 237 | 9,493 | 1,957 |
| `copilotkit-foundation` | 1,484 | 303 | 15,294 | 2,549 |
| `crawl4ai-foundation` | 690 | 210 | 6,380 | 1,765 |
| `crewai-foundation` | 2,517 | 199 | 23,085 | 1,679 |
| `cuga-agent-foundation` | 14,147 | 291 | 123,679 | 2,549 |
| `dagster-foundation` | 829 | 215 | 8,613 | 1,842 |
| `dify-foundation` | 1,063 | 230 | 10,673 | 1,884 |
| `django-foundation` | 721 | 200 | 6,796 | 1,692 |
| `dnd-kit-foundation` | 936 | 203 | 9,662 | 1,752 |
| `docmost-foundation` | 742 | 200 | 6,406 | 1,698 |
| `dsh-codex-foundation` | 2,929 | 298 | 26,682 | 2,613 |
| `dsh-factory-foundation` | 842 | 204 | 7,661 | 1,788 |
| `dsh-template-foundation` | 1,184 | 219 | 10,852 | 1,888 |
| `dub-foundation` | 12,673 | 228 | 118,919 | 1,930 |
| `duckdb-foundation` | 1,379 | 213 | 14,031 | 1,764 |
| `duckdb-vectorized-foundation` | 949 | 235 | 8,107 | 1,978 |
| `easyappointments-foundation` | 1,084 | 211 | 9,691 | 1,892 |
| `ell-foundation` | 1,467 | 262 | 12,606 | 2,139 |
| `eslint-foundation` | 3,398 | 248 | 33,665 | 2,149 |
| `fastapi-foundation` | 756 | 239 | 7,527 | 1,997 |
| `firecrawl-foundation` | 906 | 202 | 8,483 | 1,715 |
| `flask-foundation` | 707 | 224 | 6,922 | 1,885 |
| `framer-motion-foundation` | 1,093 | 201 | 9,618 | 1,778 |
| `freescout-foundation` | 1,636 | 206 | 15,264 | 1,789 |
| `georank-foundation` | 1,137 | 219 | 10,666 | 1,855 |
| `geoready-foundation` | 943 | 217 | 9,138 | 1,851 |
| `ghost-foundation` | 1,666 | 259 | 14,196 | 2,208 |
| `goose-foundation` | 1,825 | 287 | 17,626 | 2,514 |
| `gpt-engineer-foundation` | 688 | 217 | 6,988 | 1,848 |
| `gpt-researcher-foundation` | 1,358 | 205 | 12,921 | 1,735 |
| `graphiti-foundation` | 2,363 | 206 | 23,720 | 1,718 |
| `graphrag-foundation` | 2,859 | 211 | 28,420 | 1,796 |
| `grist-core-foundation` | 11,408 | 295 | 106,590 | 2,645 |
| `growchief-foundation` | 2,667 | 214 | 24,433 | 1,949 |
| `headlessui-foundation` | 1,267 | 207 | 11,786 | 1,761 |
| `healthchecks-foundation` | 1,503 | 231 | 13,728 | 1,993 |
| `htmx-foundation` | 1,102 | 231 | 11,126 | 1,934 |
| `humanizer-foundation` | 748 | 251 | 5,998 | 2,126 |
| `isso-foundation` | 1,255 | 217 | 12,316 | 1,822 |
| `jetbrains-internals-foundation` | 15,600 | 200 | 145,429 | 1,735 |
| `jobspy-foundation` | 995 | 204 | 9,510 | 1,689 |
| `joplin-foundation` | 1,171 | 226 | 11,020 | 1,899 |
| `kdenlive-foundation` | 2,928 | 299 | 25,622 | 2,577 |
| `lancedb-foundation` | 796 | 210 | 7,249 | 1,759 |
| `langgraph-foundation` | 1,387 | 272 | 12,612 | 2,401 |
| `lemmy-foundation` | 1,203 | 216 | 10,578 | 1,829 |
| `lh-basis-foundation` | 1,652 | 265 | 14,580 | 2,367 |
| `linkedin-mcp-foundation` | 1,300 | 206 | 12,968 | 1,723 |
| `linkedin-scrapers-foundation` | 15,359 | 245 | 142,422 | 2,053 |
| `linkforty-core-foundation` | 1,095 | 241 | 9,828 | 2,057 |
| `listmonk-foundation` | 899 | 209 | 8,768 | 1,790 |
| `litellm-foundation` | 2,493 | 203 | 23,451 | 1,705 |
| `localterm-foundation` | 3,599 | 249 | 31,396 | 2,137 |
| `locoagent-foundation` | 20,162 | 210 | 199,351 | 1,817 |
| `logfire-foundation` | 740 | 198 | 7,673 | 1,702 |
| `mastra-foundation` | 1,152 | 247 | 11,419 | 2,067 |
| `mcp-spec-and-servers-foundation` | 4,788 | 238 | 44,437 | 2,095 |
| `mcp-ts-sdk-foundation` | 3,118 | 211 | 31,462 | 1,733 |
| `meetily-foundation` | 953 | 210 | 8,902 | 1,813 |
| `meilisearch-foundation` | 1,166 | 207 | 10,963 | 1,774 |
| `mem0-foundation` | 3,984 | 200 | 39,720 | 1,661 |
| `mike-foundation` | 1,074 | 214 | 9,105 | 1,822 |
| `milvus-foundation` | 970 | 243 | 9,773 | 2,074 |
| `nest-foundation` | 2,858 | 229 | 28,670 | 1,845 |
| `nexus-public-foundation` | 2,214 | 238 | 21,340 | 2,091 |
| `nocodb-foundation` | 21,212 | 296 | 192,210 | 2,528 |
| `node-best-practices-foundation` | 2,225 | 225 | 20,997 | 1,918 |
| `oh-my-pi-foundation` | 5,107 | 209 | 51,500 | 1,703 |
| `ollama-foundation` | 1,023 | 211 | 9,437 | 1,788 |
| `open-computer-use-foundation` | 656 | 203 | 5,526 | 1,749 |
| `open-interpreter-foundation` | 878 | 194 | 8,465 | 1,675 |
| `open-seo-foundation` | 930 | 270 | 8,084 | 2,261 |
| `open-webui-foundation` | 1,753 | 299 | 14,957 | 2,572 |
| `openai-agents-foundation` | 3,722 | 217 | 39,181 | 1,769 |
| `openai-swarm-foundation` | 708 | 231 | 6,278 | 1,920 |
| `opencode-foundation` | 5,807 | 199 | 56,375 | 1,678 |
| `openhands-foundation` | 1,610 | 291 | 13,570 | 2,530 |
| `openhistory-foundation` | 974 | 255 | 7,891 | 2,153 |
| `openoats-foundation` | 1,052 | 274 | 9,001 | 2,400 |
| `openoutreach-foundation` | 1,673 | 226 | 14,484 | 1,909 |
| `openproject-foundation` | 519 | 223 | 5,143 | 1,955 |
| `openreplay-foundation` | 2,372 | 223 | 20,342 | 1,934 |
| `openserp-foundation` | 1,766 | 208 | 15,272 | 1,745 |
| `os-clovy-foundation` | 980 | 263 | 8,698 | 2,292 |
| `palmier-pro-foundation` | 926 | 243 | 7,697 | 1,988 |
| `paperqa-foundation` | 965 | 201 | 9,842 | 1,708 |
| `penpot-foundation` | 2,204 | 229 | 20,122 | 1,860 |
| `pi-acp-foundation` | 6,196 | 251 | 59,019 | 2,020 |
| `pi-autoresearch-foundation` | 1,328 | 228 | 11,664 | 2,050 |
| `pi-better-openai-foundation` | 2,218 | 230 | 20,315 | 1,960 |
| `pi-fabric-foundation` | 3,962 | 288 | 39,442 | 2,569 |
| `pi-fovea-foundation` | 2,489 | 233 | 21,362 | 1,996 |
| `pi-hypercharm-provider-foundation` | 1,755 | 246 | 16,193 | 2,135 |
| `pi-messenger-swarm-foundation` | 1,297 | 254 | 12,858 | 2,140 |
| `pi-mono-foundation` | 1,196 | 236 | 10,555 | 2,100 |
| `pi-multi-pass-foundation` | 897 | 224 | 7,469 | 1,939 |
| `pi-provider-kimi-code-foundation` | 902 | 257 | 7,495 | 2,218 |
| `pi-supervisor-foundation` | 2,197 | 243 | 21,546 | 2,108 |
| `pi-upstream-foundation` | 2,332 | 219 | 21,043 | 1,820 |
| `pipeshub-ai-foundation` | 11,648 | 212 | 111,961 | 1,777 |
| `plane-foundation` | 1,163 | 241 | 9,713 | 2,018 |
| `playwright-foundation` | 1,627 | 224 | 13,947 | 1,933 |
| `postal-foundation` | 1,677 | 213 | 14,168 | 1,789 |
| `praisonai-foundation` | 601 | 245 | 5,066 | 2,103 |
| `prefect-foundation` | 1,561 | 283 | 14,703 | 2,475 |
| `pydantic-ai-foundation` | 10,154 | 277 | 99,229 | 2,566 |
| `pydantic-ai-harness-foundation` | 2,707 | 236 | 27,141 | 2,055 |
| `pydantic-core-foundation` | 1,443 | 223 | 13,347 | 1,898 |
| `pydantic-foundation` | 1,798 | 230 | 17,340 | 1,991 |
| `pydantic-settings-foundation` | 761 | 229 | 6,495 | 1,982 |
| `qdrant-foundation` | 2,128 | 221 | 18,539 | 1,906 |
| `qodana-action-foundation` | 1,707 | 230 | 15,201 | 2,035 |
| `quickbeam-foundation` | 2,563 | 236 | 25,938 | 2,016 |
| `radix-ui-foundation` | 1,393 | 204 | 13,144 | 1,745 |
| `ragflow-foundation` | 1,557 | 202 | 13,986 | 1,701 |
| `railway-nexus3-foundation` | 1,031 | 214 | 9,232 | 1,854 |
| `rallly-foundation` | 2,061 | 216 | 17,260 | 1,858 |
| `react-foundation` | 988 | 229 | 8,355 | 2,026 |
| `recharts-foundation` | 828 | 215 | 7,629 | 1,818 |
| `refined-github-foundation` | 2,160 | 218 | 21,967 | 1,808 |
| `relaticle-foundation` | 3,505 | 304 | 34,660 | 2,655 |
| `requests-foundation` | 1,413 | 197 | 13,420 | 1,699 |
| `roo-foundation` | 4,979 | 290 | 46,464 | 2,552 |
| `rsbuild-foundation` | 4,122 | 243 | 38,071 | 2,098 |
| `screenity-foundation` | 941 | 249 | 8,349 | 2,176 |
| `semantic-kernel-foundation` | 4,276 | 293 | 36,487 | 2,594 |
| `server-foundation` | 738 | 246 | 6,727 | 2,095 |
| `shadcn-ui-foundation` | 1,104 | 295 | 9,715 | 2,587 |
| `sharex-foundation` | 757 | 228 | 6,950 | 1,890 |
| `skills-foundation` | 3,458 | 315 | 29,082 | 2,514 |
| `smolagents-foundation` | 1,233 | 194 | 12,903 | 1,627 |
| `solid-foundation` | 1,356 | 208 | 12,234 | 1,743 |
| `starlette-foundation` | 1,495 | 279 | 15,317 | 2,531 |
| `storm-foundation` | 948 | 192 | 9,643 | 1,664 |
| `strapi-foundation` | 1,756 | 269 | 15,111 | 2,500 |
| `supabase-foundation` | 2,899 | 299 | 24,469 | 2,612 |
| `superset-foundation` | 1,252 | 279 | 11,837 | 2,458 |
| `svelte-foundation` | 808 | 265 | 6,947 | 2,276 |
| `sweep-foundation` | 3,680 | 299 | 30,945 | 2,595 |
| `tailwindcss-foundation` | 707 | 244 | 5,880 | 2,055 |
| `tanstack-query-foundation` | 1,029 | 244 | 9,514 | 2,134 |
| `teable-foundation` | 16,189 | 260 | 156,938 | 2,284 |
| `theagenticbrowser-foundation` | 2,245 | 213 | 20,945 | 1,894 |
| `turso-foundation` | 6,887 | 214 | 69,768 | 1,707 |
| `twenty-crm-foundation` | 1,753 | 298 | 16,849 | 2,643 |
| `txtai-foundation` | 1,067 | 219 | 10,394 | 1,832 |
| `typechat-foundation` | 816 | 207 | 7,600 | 1,800 |
| `ufo-foundation` | 871 | 277 | 7,909 | 2,419 |
| `ui-ant-design-foundation` | 894 | 240 | 8,052 | 2,125 |
| `ui-daisyui-foundation` | 560 | 222 | 4,968 | 1,940 |
| `ultireaaach-foundation` | 737 | 268 | 5,939 | 2,199 |
| `umami-foundation` | 1,094 | 240 | 10,237 | 2,028 |
| `uvicorn-foundation` | 1,495 | 234 | 12,124 | 1,980 |
| `vaultwarden-foundation` | 894 | 218 | 8,404 | 1,887 |
| `veda-foundation` | 4,427 | 205 | 40,080 | 1,781 |
| `visx-foundation` | 1,281 | 244 | 11,074 | 2,096 |
| `vitest-foundation` | 1,960 | 216 | 18,286 | 1,827 |
| `vue-core-foundation` | 802 | 212 | 6,806 | 1,810 |
| `weaviate-foundation` | 1,076 | 214 | 10,052 | 1,950 |
| `zendriver-foundation` | 680 | 219 | 6,535 | 1,834 |
| `zep-foundation` | 1,027 | 212 | 8,663 | 1,834 |
