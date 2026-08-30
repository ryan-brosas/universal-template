<!-- capsule-v2 -->
# Profile composition patch — how does an optional provider bundle ship composition defaults into a host profile as patch rows that saved user settings still override, including a capability-optional terminal front door?

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** How does an optional provider bundle ship composition defaults into a host profile as patch rows that saved user settings still override, including a capability-optional terminal front door?

## Repo-owned YAML patch over the host's base composition
**Path/Symbol:** `cordis.patch.yml` (whole file, `:1-20`) — the PROFILE-level counterpart of the apply()-time ordering owned by plugin-assembly-order.
**Signature:** Not a callable; a declarative Cordis patch document: overlay rows (`id` + `config`) plus an `insert:` block of bundle/front-door rows.
**Data Shape:** Two overlay rows — `agent-default-model {provider: openai-codex, model: gpt-5.6-sol}` and `web {searchProvider: openai-codex}`; one insert block adding the `llm-openai-codex` bundle row (`name: dsh-codex`) and an optional `openai-codex-tui` front door (`name: dsh-codex/tui`, `inject: [openAICodex]`).

### Decisive source
```yaml
# cordis.patch.yml :1-20 (whole)
# Optional ChatGPT subscription route over the base composition. The saved
# agent-default-model setting, when present, still wins over this bundle value.

- id: agent-default-model
  config:
    provider: openai-codex
    model: gpt-5.6-sol

- id: web
  config:
    searchProvider: openai-codex

- insert:
    - id: llm-openai-codex
      name: dsh-codex
    # Optional terminal front-door adapter. It stays dormant on Web because
    # tuiWorkspaces is absent, and contributes /codex when dsh-tui is mounted.
    - id: openai-codex-tui
      name: dsh-codex/tui
      inject: [openAICodex]
```

**Flow:** host loads its base composition → this patch overlays defaults onto existing rows and inserts the provider bundle + terminal door → saved user settings (already persisted) win over the bundled default per the header comment → the tui door stays dormant wherever the TUI workspace service is absent because it declares its dependency via `inject`.
**Invariant:** A patch is defaulting/additive only — it must never clobber saved user settings; every optional front door must scope itself with `inject` so absence of its dependency keeps the row inert instead of erroring at load.
**Probe:** `tests/loader-composition.spec.ts` (boundary evidence: a REAL Cordis Loader + include plugin loads a cordis.yml whose bundle row mirrors the insert block — `id: llm-openai-codex, name: dsh-codex` — pins `{id:'openai-codex', name:'OpenAI Codex'}` registration plus the exact configured model list, and proves `entry.fiber.dispose()` unregisters the provider).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-codex", label: "File", qn_pattern: "cordis\\.patch", limit: 10 });
// observed live: total 1 — dsh-codex.cordis.patch.yml File node, has_more=false
```

## Verdict
Adopt "ship composition defaults as a repo-owned patch document whose rows are defaults, not overrides; make optional doors dependency-scoped." Adapt row ids/config keys to the host's loader grammar. Omit the specific Codex model/searchProvider values. Honest caveats: no dedicated spec executes cordis.patch.yml itself (the Loader test proves the mechanics with a mirror fixture); docs/design.md §Composition corroborates precedence but is documentation, kept out of the anchors.
