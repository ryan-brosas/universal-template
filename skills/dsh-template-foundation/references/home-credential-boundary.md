<!-- capsule-v2 -->
# Home credential boundary — `$DSH_HOME/.credentials.yaml` + `${VAR}` expansion

**Source:** dsh-template (no LICENSE, `pi-fovea-foundation@ffb36822ffbcbba509deebaf3ea9412a9ea8b2c4`); Codebase Memory `dsh-template`. **Question:** Where exactly do credentials live in the DSH home-config model, and how are secret references written in committed templates so they never leak real values?

## Credential placement + env-var expansion contract
**Path/Symbol:** `.dsh/home/README.md:1-13` (whole file, 13 lines) — the credential sentence (`:11-12`) and the file→destination table (`:6-9`). Companion files (already captured): `.dsh/home/settings.yaml`, `.dsh/home/mcp.yaml`. Graph: `search_code --pattern 'credentials'` resolves the `.dsh/home.README` Module line-exact.
**Signature:** `Credentials belong in $DSH_HOME/.credentials.yaml or environment variables (${VAR} references are expanded by DSH).` — one sentence, two legal homes for secrets, one expansion mechanism.
**Data Shape:** destination table maps template → live path: `.dsh/home/settings.yaml` → `$DSH_HOME/settings.yaml` (models/providers, default agent preset, agent-loop tuning); `.dsh/home/mcp.yaml` → `$DSH_HOME/mcp.yaml` (MCP servers). `$DSH_HOME` defaults to `~/.dsh`.

### Decisive source
```markdown
# $DSH_HOME config templates

These are templates for the DeepSeek Harness home config, default
`$DSH_HOME` = `~/.dsh`. Copy and adapt; never commit real secrets.

| File | Destination | Purpose |
| --- | --- | --- |
| `settings.yaml` | `$DSH_HOME/settings.yaml` | Models/providers, default agent preset, agent-loop tuning |
| `mcp.yaml` | `$DSH_HOME/mcp.yaml` | MCP servers (Codebase Memory, Exa, Context7, DeepWiki, ...) |

Credentials belong in `$DSH_HOME/.credentials.yaml` or environment variables
(`${VAR}` references are expanded by DSH).
```

**Flow:** (1) author committed templates with `${ENV_VAR}` placeholder references only — e.g. `mcp.yaml`'s `env: { EXA_API_KEY: "${EXA_API_KEY}" }`; (2) at copy/deploy time place real values either in `$DSH_HOME/.credentials.yaml` or as environment variables; (3) DSH expands `${VAR}` references when reading home config; (4) the template repo itself never contains a real secret.

**Invariant:** exactly two legal credential homes (`.credentials.yaml` or env vars); committed templates carry only `${VAR}` references, which DSH expands — a porter who bakes literal keys into templates breaks the boundary this layout exists to enforce.

**Probe:** no direct test file exists. Deterministic probes executed at HEAD: `grep -c 'expanded by DSH' .dsh/home/README.md` → 1; `grep -c 'EXA_API_KEY: "\${EXA_API_KEY}"' .dsh/home/mcp.yaml` → 1 (placeholder-only evidence). Coverage caveat: expansion is implemented host-side (the harness), not in this template.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dsh-template", query: "credentials", limit: 10, fields: ["signature", "name", "file"] });
// doc-shaped graph fallback:
// codebase-memory-mcp cli search_code --project dsh-template --pattern 'credentials'
```

## Verdict
Adopt the two-home credential rule and the `${VAR}`-placeholder-only committed-template discipline with harness-side expansion. Adapt the credential filename and the server list to the host. Omit `.credentials.yaml` support if the host has its own secret store (keep the placeholder-only invariant).
