# Replicate a merged fork change upstream

Use when contributing an already-merged fork change upstream, or explaining why
its destination PR differs. Replication is a content claim, not permission to
redesign the feature. A scope-comparison request stays read-only.

## Pin the source and destination

Identify both repositories explicitly; follow the
[GitHub target guard](../../gh-repo-target-guard/README.md). Record the source PR's
base, reviewed head and merge commit, and the destination PR's base and current
head. Do not substitute today's fork `main` for the accepted source revision.

For each PR, inspect its three-dot diff from its own pinned base:

```sh
git diff --name-status <source-base>...<source-head>
git diff --name-status <destination-base>...<destination-head>
```

A tip-to-tip comparison between repositories includes upstream evolution and is
not the destination PR's scope. When using GitHub's changed-file API instead,
read every page and retain rename information.

## Explain content, not just counts

Compare the path sets: destination-only, source-only and shared. Inspect shared
files' hunks too; equal paths or counts do not establish equal content. Account
for renames and splits rather than assuming every additional path is a new
feature or every missing path is lost work.

Trace the destination's integration and follow-up commits. Show when its path
count changed and which commits first introduced the extra paths into the diff.
A later fix to an already-listed file does not increase that count. Do not blame
base drift for extra files without checking the actual patches.

Classify the changes by purpose:

- **Accepted feature:** implementation, tests, documentation and evidence tooling
  already included in the merged source.
- **Integration adaptations:** dependency/API compatibility, import wiring or
  build-constraint changes needed on the destination base. Verify these rather
  than calling a refactor behavior-preserving from its name alone.
- **Independent fixes:** general runtime, platform or CI repairs discovered while
  integrating. Explain why they were bundled; passing CI does not make them
  feature work. The accepted fork may already contain such repairs.

If the result includes adaptations or independent fixes, call it an integration
with follow-up changes, not an exact replica. For strict feature-only scope,
propose separating independent repairs and disclose any resulting CI dependency;
do not silently revert them or expand the task to repair them.

## Exclude concurrent work

Compare committed revisions, not the shared dirty checkout. Check both untracked
paths and overlapping-file hunks: an unrelated edit can ride inside a legitimate
feature file. Absence of a new filename is not proof of absence of unrelated work.
Do not overwrite newer upstream content with whole files from the fork to force
matching counts.

## Keep the verdicts separate

Report source/destination revisions, content differences, dispositions and
remaining gaps. Scope fidelity, CI status and review completeness are independent.
Use [pre-PR validation](../../pre-pr-validation/README.md) for review coverage and
[CI observation](../../push-pr/references/ci-and-observation.md) for the current
head's checks. An unavailable review lane or unresolved import is not an all-path
clean verdict; a scope audit does not close those gaps.
