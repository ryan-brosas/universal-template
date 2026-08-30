<!-- capsule-v2 -->
# Sweep-PR cron maintenance — how do you keep bot-created PR branches mergeable across days without a worker per PR?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** What does a single external cron tick do to a repo's open bot PRs, and which PRs get closed vs kept current?

## update_sweep_prs_v2: recency-capped scan, base-into-head merge, [Sweep Rules] 24h close rule
**Path/Symbol:** `sweepai/api.py:update_sweep_prs_v2` (:306–362); chain target `sweepai/handlers/create_pr.py:create_gha_pr` (:260).
**Signature:** `update_sweep_prs_v2(repo_full_name: str, installation_id: int)` on `@app.get("/update_sweep_prs_v2")` — an unauthenticated GET endpoint hit by an EXTERNAL cron (no in-repo caller; comment "# Set up cronjob for this").
**Data Shape:** PyGithub objects; `repo.get_pulls(state="open", head="sweep", sort="updated", direction="desc")[:5]` — the `head="sweep"` filter matches both `sweep/` and `sweep_` branch prefixes, and the slice caps work to the 5 most recently updated PRs.

### Decisive source
```python
try:
    branch_ttl = int(config.get("branch_ttl", 7))
except Exception:
    branch_ttl = 7
branch_ttl = max(branch_ttl, 1)          # computed, then NEVER USED at pin (dead clamp)
...
for pr in pulls:
    try:
        feature_branch = pr.head.ref
        if not feature_branch.startswith("sweep/") and not feature_branch.startswith("sweep_"):
            continue
        if "Resolve merge conflicts" in pr.title:
            continue
        if (pr.mergeable_state != "clean"
                and (time.time() - pr.created_at.timestamp()) > 60 * 60 * 24
                and pr.title.startswith("[Sweep Rules]")):
            pr.edit(state="closed")
            continue
        repo.merge(feature_branch, pr.base.ref, f"Merge main into {feature_branch}")
        if pr.title == "Configure Sweep" and pr.merged:
            create_gha_pr(g, repo)
    except Exception as e:
        logger.warning(f"Failed to merge changes from default branch into PR #{pr.number}: {e}")
```

**Flow:** cron tick → fetch ≤5 most-recently-updated open bot-head PRs → per PR: prefix gate (`sweep/` or `sweep_`) → skip conflict-resolution PRs → close rule (dirty + older than 24h + `[Sweep Rules]` title ⇒ close, never merge) → otherwise `repo.merge(head=feature_branch, base=pr.base.ref)` which merges the DEFAULT BRANCH INTO the sweep branch (keeps the bot branch current; it never merges the PR itself) → if the "Configure Sweep" PR has since been human-merged (`pr.merged`), create the follow-up GHA PR. Every failure is a logged warning; the outer try/except swallows even the whole-batch failure.
**Invariant:** The batch is fail-soft by construction: one bad PR must never stop the others (per-PR except), and the endpoint itself must never 500 the cron (outer except). The close rule is deliberately narrow — only `[Sweep Rules]` PRs are auto-closed, and only after 24h of being unmergeable; ordinary ticket PRs stay open forever until merged or manually closed. The `branch_ttl` config read with its `max(ttl, 1)` clamp is DEAD CODE at pin (computed, never consumed) — a port should either wire it to a real TTL-close path or delete it, not copy it. The endpoint has NO auth at pin (Sweep ran it behind their own infra); a port must add authentication before exposing it.
**Probe:** No offline unit test exists (live-GitHub harness only — coverage caveat). Deterministic probes at pin: `grep -c 'branch_ttl' sweepai/api.py` → 3 (all inside this function, none consumed); `grep -rn 'update_sweep_prs' --include='*.py' .` → only the definition (no in-repo caller); `grep -n 'def create_gha_pr' sweepai/handlers/create_pr.py` → :260.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "update sweep prs cron merge default branch into pull request", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source read of
// api.py:306-362 + create_pr.py:260 at pin substituted — see verification.md pass 3.
```

## Verdict
Adopt the recency-capped scan (bounded work per tick), the base-into-head merge that keeps bot branches current without touching PR state, the narrow title+age+mergeable-state auto-close rule, and the double try/except fail-soft batch. Adapt the branch-prefix gate and config-PR→GHA-PR chain to your provisioning flow; add auth. Omit the dead `branch_ttl` clamp unless you implement a real TTL-close path.
