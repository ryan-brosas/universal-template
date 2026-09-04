<!-- capsule-v2 -->
# Agent-assigned sweep issue — how does graphrag hand a dependency sweep to Copilot coding agent via one POST?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory project `graphrag`. **Question:** What exact issue payload makes GitHub's Copilot coding agent open a PR that runs this repo's own `update-deps` skill — and which fields are load-bearing?

## Key facts
**Path/Symbol:** `scripts/open-deps-update-issue.ts` (`body` object :11-23; POST :25-36).
**Signature:** module script (Bun): builds one JSON body and POSTs to `/repos/{owner}/{repo}/issues`; prints the created issue JSON.
**Data Shape:** standard issue fields (`title`, `body`, `labels: ["dependencies"]`) PLUS the agent-assignment extension: `assignees: ["copilot-swe-agent[bot]"]` and an `agent_assignment` object `{ target_repo, base_branch: "main", custom_instructions, model }`.

### Decisive source
```ts
// scripts/open-deps-update-issue.ts :11-23 — the whole contract is the body shape:
const body = {
  title: "Update Dependencies Sweep",
  body: "Update dependencies to the latest versions. ...",
  labels: ["dependencies"],
  assignees: ["copilot-swe-agent[bot]"],
  agent_assignment: {
    target_repo: `${OWNER}/${REPO}`,
    base_branch: "main",
    custom_instructions:
      "Use the update-deps skill to update all dependencies to their latest versions.",
    model: "claude-opus-4.8",
  },
};
```

**Flow:** throw-at-boot on missing `GH_APP_ACCESS_TOKEN` (:3-6) → single POST `/issues` → `!res.ok` throws with status text (:38-40) → success dumps the created issue JSON (:42-44).
**Invariant:** the `agent_assignment.custom_instructions` string names the repo's OWN `.agents/skills/update-deps/SKILL.md` by name ("Use the update-deps skill...") — the skill file IS the instruction surface, and the issue only points at it. Changing the model id or instructions requires no workflow edit. The pair with close-dependabot-prs (same cron slot, see dependabot-suppression-closure capsule) means every scheduled window both closes old bot PRs AND opens exactly ONE new agent-authored sweep issue.
**Probe:** `grep -c 'agent_assignment' scripts/open-deps-update-issue.ts` = 1 (:16); `grep -c 'GH_APP_ACCESS_TOKEN' scripts/open-deps-update-issue.ts` = 2 (:3,:30). No dedicated test suite exists for this script (coverage caveat: CI-workflow smoke only).

## Get live surrounding code
**Retrieve:** BM25 carries zero tokens for this doc-shaped TS node — use search_code (drift note: BM25 `search_graph` total:0 here is by-construction):
```
codebase-memory-mcp cli search_code '{"project":"graphrag","pattern":"agent_assignment"}'
```
resolves `graphrag.scripts.open-deps-update-issue.body` :11-23 line-exact.

## Verdict
Adopt the issue-as-agent-dispatch pattern (labels + bot assignee + `agent_assignment` block pointing at a repo-owned skill); adapt repo constants, model choice, and instruction wording; omit nothing — the file is 44 lines and fully captured. Coverage: `no_recorded_issue`; no direct unit test pins this file.
