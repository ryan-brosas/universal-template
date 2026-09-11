# Evidence capability map

Cold reference. Resolve code questions from the nearest sufficient evidence; no
tool is a mandatory first step.

**Default:** the current project's source and tests, using the tools the host
already has — filesystem search, Git, IDE/LSP, compiler and test output.

| Need | Capability |
|---|---|
| Local project orientation, known file/symbol | Direct source, Git, IDE/LSP (`fovea_*` when available) |
| Cross-repository or architectural question | Indexed source (Sourcebot profile `cross-repo-source`): `list_repos` → `grep`/`glob`/`find_symbol_*` → `read_file`/`list_commits` |
| Implementation outside the indexed corpus | GitHub or equivalent source discovery, then read the actual source |
| Current library/framework behavior | installed source, official docs, or Context7 |
| Runtime behavior | tests, debugger, runtime output |
| IDE-aware types / semantic refactor of the active project | `ide` profile: MCP Steroid / JetBrains (`steroid_*`) |
| Live site capture / browser | `reference/web/<site>/` or CDP |
| Past attempts / lessons | project-scoped session history (`/recall-session`) |
| External facts / advisories | Exa or read-only fetch |

Name one uncertainty, select its primary source, and escalate only when that
source is insufficient. Indexed results and model output are evidence, not
authority: confirm exact code before editing or making exhaustive claims. MCP
capabilities are selected per task from `../../../mcp/profiles.json`; each profile
selects at most one server and `minimal` connects none. For execution or model
escalation, see `execution-router` and `model-resolution`.
