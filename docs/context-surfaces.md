# Context surfaces and host probes

This document defines the context contract and records reproducible measurements.
The JSON companion, `context-measurements.json`, is the machine-readable result.
Measurements are version-specific evidence, not timeless host promises.

## Hot and cold sets

A tracked skill is **hot** only when it is operational (`kind` is absent) and
`disable-model-invocation` is not `true`. Its `name` and `description` may be
placed in startup context. A tracked skill is **cold** when it is hidden or is a
`kind: foundation` evidence leaf. Cold entries remain discoverable by explicit
filesystem/host search, but are not loaded into startup context. Untracked or
Git-ignored local skills are outside the publication sets.

The sets are exhaustive and disjoint by construction. Measure or gate them with:

```bash
python3 scripts/skill-catalog.py context --json
python3 scripts/skill-catalog.py context --max-hot-skills 40 --max-hot-chars 11000
```

At base commit `76afa8e`, the tracked result was 38 hot skills, 309 cold entries,
zero overlap, and 10,315 hot metadata characters (~2,578 tokens at four
characters/token). The threshold allows two deliberate additions and modest
copy edits without permitting silent catalog expansion. Change the limit only
with a new measured baseline and rationale.

## Real Pi payload probe

Pi 0.84.4 was run under a temporary config root against a one-request local
OpenAI-compatible server. The command disabled ambient skills and passed one
`--skill` path for each tracked hot entry, disabled context files/extensions and
used only the `read` tool. The fake server returned a minimal streamed response;
no real model or credential was used. The captured request contained 38 skill
entries, 18,313 system characters and 19,491 serialized request bytes. A hot
marker was present and a cold-foundation marker was absent.

This proves the explicit filtered route and the outgoing Pi payload. It does not
prove other hosts, future versions, tokenizer counts, or ambient user config.
To re-probe: create a temporary `PI_CODING_AGENT_DIR`, define a custom
OpenAI-compatible model whose base URL is a loopback capture server, set
`PI_OFFLINE=1`, and run `pi -p --no-session --no-skills` with the paths returned
by `skill-catalog.py list --surface hot --json` where `local` is false.

## Installed host matrix

Version inventory on 2026-09-04: Pi 0.84.4, Claude Code 2.1.259, Codex 0.151.0,
OpenCode 1.18.27, Cursor Agent 2026.08.11-e8db854, Agy 1.1.26, and Gemini CLI
0.58.0.

| Host | Safe evidence | Limitation / setup guidance |
| --- | --- | --- |
| Pi | Real loopback outbound payload captured as above. | Use `--no-skills` plus explicit hot paths for a provable surface. |
| Claude Code | Temporary-root discovery previously loaded all linked skills; the current loopback attempt emitted no request without authenticated CLI state. | Treat hidden-field filtering as unproved; expose a filtered directory only. |
| Codex | Temporary `CODEX_HOME` was used. `OPENAI_BASE_URL` did not redirect 0.151.0, so the attempt was stopped after an unauthorized dummy request and no payload was recorded. | Do not claim a context payload until a documented local provider route is available. |
| OpenCode | Temporary project discovery previously exposed hidden foundations. | Disable external discovery and configure a filtered hot path. |
| Gemini CLI | Temporary linked-skill inventory previously exposed hidden foundations. | Link only a filtered hot view. |
| Cursor Agent | Temporary startup exposes no inventory command and stopped before a model turn. | Treat startup behavior as unverified; configure only a filtered path. |
| Agy | Version was inventoried; no documented isolated endpoint override was established. | Do not infer context behavior from installation. |

The detailed earlier discovery commands and caveats remain in
`docs/foundation-skill-v1.md`. Only Pi had a documented, credential-free custom
provider route that made an isolated outbound payload probe safe in this run.

## MCP cost and activation

`mcp/servers.json` is a six-server registry, not a default connection set.
`mcp/profiles.json` defines explicit profiles; `minimal` activates none. Preview
one scoped merge, then apply it only on request:

```bash
python3 mcp/configure.py --profile docs --target /path/to/host.json
python3 mcp/configure.py --profile docs --target /path/to/host.json --apply
python3 mcp/configure.py --profile docs --target /path/to/host.json --deactivate --apply
```

The live adapter exposed 42 tools from the six declarations. Compact serialized
input schemas plus descriptions totaled 81,429 bytes: codebase-memory 20,379;
context7 4,437; deepwiki 697; exa 1,722; OpenViking 8,266; and MCP Steroid
45,928. The minimal profile exposes zero of those bytes, an 81,429-byte contract
reduction relative to connecting all six. This is a schema-cost comparison, not
a tokenizer or provider-billing claim. Re-measure from the active adapter after
server upgrades; package-managed npx entries are exact-version pinned.
