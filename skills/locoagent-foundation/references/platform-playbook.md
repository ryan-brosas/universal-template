<!-- capsule-v2 -->
# Platform playbook anatomy — how is a 37-operation browser skill structured so an LLM executes composite tasks in one pass?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What per-operation structure and cross-cutting conventions make a long platform playbook reliable when an agent loads it as a skill?

## Goal/Preconditions/Steps/Verification/Key Elements/Known Issues — per operation
**Path/Symbol:** `skills/x-com/SKILL.md` (1,507 lines, 7 sections, ~37 operations; frontmatter + TOC at `:1-60`); device-targeting note (`:62-67`).
**Signature:** YAML frontmatter: `description` (one-line scope), `allowed-tools: [Bash]`, `user-invocable: true`. Every operation renders the SAME six fields.
**Data Shape:** Sections group operations by capability (Browse & Read / Engagement / Content Creation / Social Graph / Profile / Navigation & Utility / Lists); each step block is copy-pasteable `agent-browser` CLI with concrete selectors.

### Decisive source
```markdown
### 1.1 Open Home Timeline

**Goal**: Navigate to the home timeline and confirm it loaded.

**Preconditions**: Logged in (Chrome CDP session with cookies).

**Steps**:
agent-browser open https://x.com/home

**Verification**:
# Title should contain "Home / X"
agent-browser get title
# Snapshot should show region "Your Home Timeline" and tab "For you"
agent-browser snapshot -i -c -s '[role="region"]'

**Key Elements**:
- Compose area: `textbox "Post text"` — inline compose on home page
- Account button: `button "Account menu"` — shows logged-in username

**Known Issues**:
- None
```
plus the cross-cutting rule:
```markdown
> **Device targeting:** Operations run against desktop Chrome by default. To
> operate the mobile web surface, set `DEVICE_PROFILE=ios|android` in `.env` ...
> When logging an action, pass `--device <target>` for provenance (it does not
> change dedup — a like is account-level).
```

**Flow:** agent receives the playbook as a skill → finds the operation matching its task → checks preconditions (login state) → runs steps verbatim → verifies via the documented observable (title/url/snapshot region) before declaring success → consults Key Elements to adapt selectors and Known Issues for traps. Verification snippets are mandatory, not optional: they convert "command exited 0" into "page state actually changed".
**Invariant:** The playbook assumes the Browser Connection Contract is already satisfied ("The per-platform playbooks assume this contract is already satisfied" — prompts.ts:421): it never logs in, never spawns browsers, and every operation ends in a verification step against named accessibility-tree roles. Device emulation changes rendering but never the dedup key.
**Probe:** No executable test (prose+commands artifact — coverage caveat). Deterministic probe: section count and six-field shape verified by reading `skills/x-com/SKILL.md`; the executor (`workflows/executors/x-search-reply.ts`) operationalizes §3.3 Reply with the same snapshot-ref pattern (`textbox "Post text"` → `@e<ref>`), proving playbook and code agree.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "playbook skill x-com operations", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the six-field per-operation anatomy, capability-grouped sections, mandatory verification snippets, and the device-provenance-not-dedup rule. Adapt all selectors and operations to your target site. Omit account-specific handles and tested-with metadata; keep the structure — it is what lets a small model finish a composite task without improvising UI flows.
