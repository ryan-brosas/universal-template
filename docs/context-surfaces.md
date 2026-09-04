# Context surfaces and host probes

This document defines the context contract and records reproducible measurements.
The JSON companion, `context-measurements.json`, is the machine-readable result.
Measurements are version-specific evidence, not timeless host promises or exact
tokenizer output.

## Static and dynamic context

The gated static global baseline is:

```text
static global context
    = AGENTS.md + hot skill names and descriptions
```

Task-selected additions are selected skill bodies and references, project-local
instructions, and active tool schemas. Conversation state contains user and
assistant history plus host/runtime state. Cold skill bodies, foundations,
generated human catalogs, and MCP schemas are not part of the static number.
MCP contract costs are reported separately because profiles activate them at
runtime.

`config/context-budget.json` is the canonical owner of the instruction, hot, and
combined limits and the character-to-token estimate divisor. Run the normal
publication check without repeated numeric limits:

```bash
python3 scripts/skill-catalog.py context
python3 scripts/skill-catalog.py context --json
```

CLI limit overrides remain available for experiments, but CI and release checks
read the config by default.

## Hot and cold sets

A tracked skill is **hot** only when it is not a foundation, has
`invocation: entry`, and does not set `disable-model-invocation: true`. Internal,
manual, vendor, and foundation leaves are **cold** in the generic cross-host
surface. Vendor capabilities may still be exposed by their owning host or
package. Untracked or Git-ignored local skills are outside publication metrics.

The measured commit has 33 hot skills with 8,449 metadata characters and 120
cold operational skills plus 194 foundations. `AGENTS.md` has 2,824 characters,
so combined static context is 11,273 characters (~2,818 tokens at
the configured four-characters-per-token estimate). The starting tree had 38
hot skills, 10,315 hot metadata characters, and a 9,484-character constitution:
19,799 combined characters (~4,949 estimated tokens).

## Real Pi payload probe

Pi 0.84.4 was run from this checkout under a temporary `PI_CODING_AGENT_DIR`
against a loopback OpenAI-compatible server. Three requests separated the base
host system, global context, and final hot surface. The runs used no session,
extensions, prompt templates, themes, ambient skills, or MCP
adapter; project trust was explicit and the only tool was `read`. The final run
passed one `--skill` path for each tracked hot entry and allowed normal
`AGENTS.md` discovery.

Measured results:

- host base system instructions: 1,748 characters;
- `AGENTS.md`: 2,824 file characters; the host-added global section delta was
  2,998 characters including its wrapper;
- hot skill metadata: 8,449 source characters; the host-added skill section
  delta was 13,950 characters including Pi's skill instructions and markup;
- selected skill-body characters: 0;
- one built-in `read` input schema: 304 compact JSON characters; its full
  serialized tool definition was 699 characters;
- final system message: 18,696 characters;
- final compact serialized request: 19,916 UTF-8 bytes.

The hot entry marker was present. The cold vendor marker `veda-worker` and the
foundation marker `aeo-affiliate-skills-foundation` were absent. Exact section
attribution beyond the file/metadata counts is not possible because Pi adds its
own wrappers and skill instructions; the control-request deltas make that
boundary explicit.

A separate two-request tool loop then explicitly selected `veda-worker`. Its
18,987-character `SKILL.md` body was absent from the 19,937-byte initial request
and entered the conversation only as the exact `read` tool result. The follow-up
request containing that body was 39,637 bytes. This proves the measured cold body
was task context, not startup context.

This proves only the isolated Pi route and outgoing payload. It does not prove
other hosts, future Pi versions, provider billing, exact tokenizer counts, or
ambient user configuration.

## Installed host matrix

Version inventory from the prior 2026-09-04 probe: Pi 0.84.4, Claude Code
2.1.259, Codex 0.151.0, OpenCode 1.18.27, Cursor Agent
2026.08.11-e8db854, Agy 1.1.26, and Gemini CLI 0.58.0.

| Host | Safe evidence | Limitation / setup guidance |
| --- | --- | --- |
| Pi | Loopback outbound payload captured as above. | Use `--no-skills` plus explicit hot paths for a provable surface. |
| Claude Code | Temporary-root discovery previously loaded all linked skills; an isolated loopback attempt emitted no request without authenticated CLI state. | Expose a filtered hot directory only. |
| Codex | `OPENAI_BASE_URL` did not redirect 0.151.0; no payload was recorded. | Do not claim a payload until a documented local provider route exists. |
| OpenCode | Temporary project discovery previously exposed hidden foundations. | Disable external discovery and configure a filtered hot path. |
| Gemini CLI | Temporary linked-skill inventory previously exposed hidden foundations. | Link only a filtered hot view. |
| Cursor Agent | Temporary startup exposed no inventory command and stopped before a model turn. | Treat startup behavior as unverified. |
| Agy | Version was inventoried; no documented isolated endpoint override was established. | Do not infer context behavior from installation. |

## MCP cost and activation

`mcp/servers.json` is a six-server registry, not a default connection set.
`mcp/profiles.json` contains single-purpose profiles: `code-graph`, `ide`,
`docs`, `repository-research`, `web-research`, and `historical-context`;
`minimal` activates none. Codebase Memory and MCP Steroid are never selected
together by a profile.

The live adapter previously exposed 42 tools from all six declarations. Compact
UTF-8 input schemas plus descriptions totaled 81,429 bytes: codebase-memory
20,379; context7 4,437; deepwiki 697; exa 1,722; OpenViking 8,266; and MCP
Steroid 45,928. These are dynamic schema costs, not part of the 11,273-character
static baseline or a provider-billing claim. Re-measure after server upgrades;
package-managed npx entries remain exact-version pinned.
