<!-- capsule-v2 -->
# Git commit resolution & builder lifecycle — how is the deploy commit resolved from ls-remote, and when does the helper container restart mid-deployment?

**Source:** Coolify Apache-2.0 `main@379abb252621f34b318190bd49b614aed9818716`; Codebase Memory `ext-coolify`. **Question:** How does `HEAD` become a concrete SHA before build secrets are injected, and why is the builder container restarted?

## prepare_builder_image / check_git_if_build_needed / restart_builder_container_with_actual_commit
**Path/Symbol:** `app/Jobs/ApplicationDeploymentJob.php:prepare_builder_image` (lines 2155–2201), `check_git_if_build_needed` (2317–2409), `restart_builder_container_with_actual_commit` (2202–2212), `gitLsRemoteCommand` (2306–2315).
**Signature:** `private function prepare_builder_image(bool $firstTry = true)`, `private function check_git_if_build_needed()`, `private function gitLsRemoteCommand(string $lsRemoteRef, ?string $identityFile = null): string`.
**Data Shape:** ls-remote refspec: branch deploys use exact `refs/heads/<branch>`; PRs use `refs/pull/<id>/head` (github/gitea), `refs/merge-requests/<id>/head` (gitlab); commit parsed with `\b([0-9a-fA-F]{40})(?=\s*\t)`.

### Decisive source
```php
// Find the part containing a tab (the actual ls-remote result)
// Handle cases where warning is on the same line as the result
if ($lsRemoteOutput->contains("\t")) {
    $output = $lsRemoteOutput->value();
    // A valid commit SHA is 40 hex characters
    preg_match('/\b([0-9a-fA-F]{40})(?=\s*\t)/', $output, $matches);
    if (isset($matches[1])) {
        $this->commit = $matches[1];
        $this->application_deployment_queue->commit = $this->commit;
        $this->application_deployment_queue->save();
    }
}
...
if ($this->application->settings->use_build_secrets && $this->commit !== 'HEAD') {
    ... 'Restarting helper container with actual SOURCE_COMMIT value.'
    $this->restart_builder_container_with_actual_commit();
}
```

**Flow:** prepare_builder_image runs helper image (`coolifyHelperImage():<version>`) attached to the destination network, mounting docker socket + buildx dir + optional registry config (build servers REQUIRE ~/.docker/config.json else DeploymentException), then runs pre-deployment command → check_git: private-key path written inside container via base64 → chmod 600 → ls-remote saved under `git_commit_sha` → SHA extracted tolerating git warnings on stdout (tab-anchored regex) and persisted to queue row → set_coolify_variables → if build secrets enabled AND commit was still HEAD, the whole builder container is shut down and re-prepared so env flags carry the REAL SOURCE_COMMIT (`env_args` cache nulled first) → clone_repository checks out, captures `git log -1 --pretty=%B` message back onto all queue rows sharing that commit.
**Invariant:** The exact-refspec ls-remote prevents `changeset-release/main` style shadow matches; SHA extraction requires tab adjacency so warning lines can't fake a match; SOURCE_COMMIT must not be baked into build-time env until it's real (see env-var-pipeline capsule) — hence the restart dance only when `use_build_secrets`. Rollbacks skip re-resolution (`! $this->rollback && shouldResolveBranchHeadCommit()`).
**Probe:** `tests/Unit/GitLsRemoteParsingTest.php` pins output parsing; `tests/Unit/ApplicationDeploymentJobCommitResolutionTest.php` pins commit resolution; live probe: `grep -n "refs/merge-requests" app/Jobs/ApplicationDeploymentJob.php` → exactly one line (2342).
**Retrieve:** search_graph project ext-coolify query "prepare_builder_image ApplicationDeploymentJob" → Method node app/Jobs/ApplicationDeploymentJob.php 2155+.

## Verdict
Adopt two-phase commit resolution + secret-aware builder restart as portable CI behavior; adapt GitHub App repo-id reconciliation and provider refspecs to your forge; omit preserve-repository mode.
